from __future__ import annotations

import asyncio
import base64
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .models import (
    ImageRequest,
    ImageResponse,
    VideoCreateRequest,
    VideoCreateResponse,
    VideoQueryResponse,
)


class AgnesClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._settings.base_url}{path}"
        async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(url, headers=self._headers, json=payload)
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._settings.base_url}{path}"
        async with httpx.AsyncClient(timeout=60.0, proxy=None) as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url, headers=self._headers)
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def generate_image(
        self,
        req: ImageRequest,
        save_to: Path | None = None,
    ) -> ImageResponse:
        payload = req.model_dump(exclude_none=True)
        data = await self._post("/images/generations", payload)
        result = ImageResponse.model_validate(data)

        if save_to and result.data:
            item = result.data[0]
            if item.get("url"):
                await self._download_to(item["url"], save_to)
            elif item.get("b64_json"):
                save_to.write_bytes(base64.b64decode(item["b64_json"]))
        return result

    async def create_video_task(self, req: VideoCreateRequest) -> VideoCreateResponse:
        payload = req.model_dump(exclude_none=True)
        data = await self._post("/videos", payload)
        return VideoCreateResponse.model_validate(data)

    async def query_video(self, video_id: str, model_name: str | None = None) -> VideoQueryResponse:
        suffix = f"?video_id={video_id}"
        if model_name:
            suffix += f"&model_name={model_name}"
        url = f"{self._settings.host}/agnesapi{suffix}"
        async with httpx.AsyncClient(timeout=60.0, proxy=None) as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url, headers=self._headers)
                    resp.raise_for_status()
                    data = resp.json()
                    return VideoQueryResponse.model_validate(data)
                except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def query_video_legacy(self, task_id: str) -> VideoQueryResponse:
        url = f"{self._settings.base_url}/videos/{task_id}"
        async with httpx.AsyncClient(timeout=60.0, proxy=None) as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url, headers=self._headers)
                    resp.raise_for_status()
                    return VideoQueryResponse.model_validate(resp.json())
                except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def generate_video(
        self,
        req: VideoCreateRequest,
        save_to: Path,
        *,
        poll_interval: float | None = None,
        poll_timeout: float | None = None,
        on_progress: Any = None,
    ) -> VideoQueryResponse:
        interval = poll_interval or self._settings.poll_interval_sec
        timeout = poll_timeout or self._settings.poll_timeout_sec
        model_name = req.model

        task = await self.create_video_task(req)
        video_id = task.video_id or task.task_id
        if not video_id:
            raise RuntimeError(f"未返回 video_id / task_id: {task.model_dump()}")

        deadline = time.monotonic() + timeout
        last: VideoQueryResponse | None = None
        post_complete_wait_max = 5
        post_complete_count = 0
        while time.monotonic() < deadline:
            await asyncio.sleep(interval)
            last = await self.query_video(video_id, model_name=model_name)
            if on_progress and last.progress is not None:
                on_progress(last.status, last.progress)
            if last.status == "failed":
                break
            if last.status == "completed":
                if last.video_url or last.url or last.output_url or last.result_url:
                    break
                post_complete_count += 1
                if post_complete_count >= post_complete_wait_max:
                    break

        if last is None or last.status != "completed":
            err = last.error if last else None
            raise RuntimeError(
                f"视频任务未完成,最后状态={last.status if last else 'unknown'},"
                f" 错误={err if err else '无'}"
            )

        video_url = (
            last.video_url
            or last.url
            or last.output_url
            or last.result_url
            or last.remixed_from_video_id
        )
        if not video_url and last.id:
            try:
                legacy = await self.query_video_legacy(last.id)
                video_url = (
                    legacy.video_url
                    or legacy.url
                    or legacy.output_url
                    or legacy.result_url
                    or legacy.remixed_from_video_id
                )
                if video_url:
                    last = legacy
            except Exception:
                pass

        if not video_url:
            import json as _json
            raise RuntimeError(
                f"任务完成但未返回 video_url, 完整响应: {_json.dumps(last.model_dump(), ensure_ascii=False)}"
            )

        await self._download_to(video_url, save_to)
        last.video_url = video_url
        return last

    @staticmethod
    async def _download_to(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True, proxy=None) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                        f.write(chunk)

    @staticmethod
    def local_image_to_data_uri(path: str | Path, max_side: int = 768) -> str:
        src = Path(path)
        if not src.exists():
            raise FileNotFoundError(f"图片不存在: {src}")

        suffix = src.suffix.lower()
        needs_convert = suffix in {".heic", ".heif"} or suffix not in {".png"}

        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            if needs_convert:
                if not shutil.which("sips"):
                    raise RuntimeError("HEIC 转换需要 macOS 自带的 sips,但未找到。")
                converted = workdir / "converted.png"
                cmd = [
                    "sips",
                    "-s", "format", "png",
                    "-Z", str(max_side),
                    str(src),
                    "--out", str(converted),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0 or not converted.exists():
                    raise RuntimeError(f"sips 转换失败: {result.stderr or result.stdout}")
                data = converted.read_bytes()
            else:
                data = src.read_bytes()
            mime = "image/png"

        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{encoded}"
