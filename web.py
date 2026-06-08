from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from flask import Flask, jsonify, render_template, request, send_from_directory
from pydantic import ValidationError

from src.client import AgnesClient
from src.config import Settings
from src.log import RunLog
from src.models import ImageRequest, VideoCreateRequest

app = Flask(__name__)

OUTPUT_DIR = Path("output")
SENSENOVA_BASE_URL = "https://token.sensenova.cn/v1"
SENSENOVA_VALID_SIZES = {
    "1664x2496", "2496x1664", "1760x2368", "2368x1760",
    "1824x2272", "2272x1824", "2048x2048",
    "2752x1536", "1536x2752", "3072x1376", "1344x3136",
}
SENSENOVA_DEFAULT_SIZE = "2752x1536"


def _download_and_save(url: str, suffix: str = ".png") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}-{uuid.uuid4().hex[:8]}{suffix}"
    dest = OUTPUT_DIR / filename
    asyncio.run(AgnesClient._download_to(url, dest))
    return f"/output/{filename}"


async def _sensenova_chat(
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 2000,
) -> dict:
    if not api_key:
        raise RuntimeError("SENSENOVA_API_KEY 未配置，请在 .env 中设置")
    url = f"{SENSENOVA_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code == 404:
            raise RuntimeError(
                f"SenseNova API 返回 404。请确认模型名 '{model}' 是否正确，"
                f"以及 SENSENOVA_API_KEY 是否有效。"
            )
        resp.raise_for_status()
        return resp.json()


async def _expand_prompt(settings: Settings, prompt: str) -> str:
    if not settings.sensenova_api_key:
        return prompt
    system_msg = (
        "You are a prompt expansion expert for image generation models. "
        "Rewrite the user's short description into a detailed, high-quality "
        "English prompt. Return ONLY the expanded prompt, no explanation."
    )
    try:
        data = await _sensenova_chat(
            settings.sensenova_api_key,
            "sensenova-6.7-flash-lite",
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
        )
        expanded = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return expanded.strip() or prompt
    except Exception:
        return prompt


async def _sensenova_generate_image(
    settings: Settings,
    prompt: str,
    size: str,
) -> str:
    if not settings.sensenova_api_key:
        raise RuntimeError("SENSENOVA_API_KEY 未配置，请在 .env 中设置")

    if size not in SENSENOVA_VALID_SIZES:
        size = SENSENOVA_DEFAULT_SIZE

    url = f"{SENSENOVA_BASE_URL}/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.sensenova_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sensenova-u1-fast",
        "prompt": prompt,
        "size": size,
        "n": 1,
    }
    async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            body = resp.text
            raise RuntimeError(
                f"SenseNova API 返回 {resp.status_code}: {body[:500]}"
            )
        data = resp.json()

    items = data.get("data", [])
    if not items:
        raise RuntimeError("sensenova-u1-fast 返回空结果")
    image_url = items[0].get("url")
    if not image_url:
        raise RuntimeError(f"sensenova-u1-fast 响应中未找到图片 URL: {data}")
    return image_url


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/image", methods=["POST"])
def api_image():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "缺少 prompt"}), 400

    settings = Settings.from_env()
    model = data.get("model", "agnes-image-2.1-flash")
    prompt = data["prompt"]
    log = RunLog()

    if data.get("expand_prompt"):
        try:
            expanded = asyncio.run(_expand_prompt(settings, prompt))
            prompt = expanded
        except Exception as e:
            return jsonify({"warning": f"提示词扩写失败: {e}"}), 200

    if model == "sensenova-u1-fast":
        try:
            url = asyncio.run(_sensenova_generate_image(settings, prompt, data.get("size", "2752x1536")))
            local_path = _download_and_save(url, ".png")
            log.append("image", {"model": model, "prompt": prompt, "size": data.get("size")}, {"path": local_path, "original_url": url})
            return jsonify({"url": local_path, "original_url": url})
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 502

    client = AgnesClient(settings)
    extra_body = {"response_format": "url"}
    req = ImageRequest(
        prompt=prompt,
        size=data.get("size", "1152x768"),
        model=model,
        image=[data["image"]] if data.get("image") else None,
        extra_body=extra_body,
    )

    try:
        resp = asyncio.run(client.generate_image(req, save_to=None))
        if not resp.data:
            return jsonify({"error": "API 返回空结果"}), 502
        item = resp.data[0]
        url = item.get("url")
        if not url:
            return jsonify({"error": "API 未返回 URL"}), 502
        local_path = _download_and_save(url, ".png")
        log.append("image", {"model": model, "prompt": prompt, "size": data.get("size")}, {"path": local_path, "original_url": url})
        return jsonify({"url": local_path, "original_url": url})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/video", methods=["POST"])
def api_video():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "缺少 prompt"}), 400

    settings = Settings.from_env()
    client = AgnesClient(settings)
    log = RunLog()

    try:
        req = VideoCreateRequest(
            prompt=data["prompt"],
            model=data.get("model", "agnes-video-v2.0"),
            width=data.get("width", 1152),
            height=data.get("height", 768),
            num_frames=data.get("frames", 121),
            frame_rate=data.get("fps", 24),
            seed=data.get("seed"),
            negative_prompt=data.get("negative_prompt"),
        )
    except ValidationError as e:
        return jsonify({"error": f"参数验证失败: {e.errors()}"}), 400

    try:
        task = asyncio.run(client.create_video_task(req))
        video_id = task.video_id or task.task_id
        if not video_id:
            return jsonify({"error": "API 未返回 task_id"}), 502
        log.append("video", req.model_dump(exclude_none=True), {"task_id": video_id})
        return jsonify({"task_id": video_id})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/video/<task_id>", methods=["GET"])
def api_video_status(task_id: str):
    settings = Settings.from_env()
    client = AgnesClient(settings)

    try:
        resp = asyncio.run(client.query_video(task_id, model_name="agnes-video-v2.0"))
        result = {
            "status": resp.status,
            "progress": resp.progress,
            "seconds": resp.seconds,
            "size": resp.size,
        }

        if resp.status == "completed":
            video_url = (
                resp.video_url or resp.url or resp.output_url or resp.result_url
            )
            if video_url:
                local_path = _download_and_save(video_url, ".mp4")
                result["url"] = local_path
                result["original_url"] = video_url

        if resp.status == "failed":
            result["error"] = str(resp.error) if resp.error else "未知错误"

        return jsonify(result)
    except RuntimeError as e:
        return jsonify({"error": str(e), "status": "failed"}), 502


@app.route("/output/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app.run(debug=True, port=5000)
