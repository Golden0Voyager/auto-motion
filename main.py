from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from src.client import AgnesClient
from src.config import Settings
from src.log import RunLog
from src.models import ImageRequest, VideoCreateRequest


def _print(msg: str) -> None:
    print(msg, file=sys.stdout, flush=True)


def _build_settings() -> Settings:
    try:
        return Settings.from_env()
    except RuntimeError as e:
        print(f"[配置错误] {e}", file=sys.stderr)
        sys.exit(2)


async def cmd_image(args: argparse.Namespace) -> int:
    settings = _build_settings()
    client = AgnesClient(settings)
    log = RunLog()

    source_input: str | None = args.image
    source_label: str
    if args.image_file:
        _print(f"[image] 读取本地源图: {args.image_file}")
        source_input = AgnesClient.local_image_to_data_uri(args.image_file)
        source_label = f"local:{args.image_file} (DataURI, {len(source_input)//1024} KB)"
    elif args.image:
        source_label = args.image
    else:
        source_label = "(无源图,纯文生图)"

    extra_body = {"response_format": "b64_json"} if args.base64 else {"response_format": "url"}
    req = ImageRequest(
        prompt=args.prompt,
        size=args.size,
        image=[source_input] if source_input else None,
        return_base64=args.base64,
        extra_body=extra_body,
    )

    out_path = Path(args.output)
    if args.base64 and out_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        out_path = out_path.with_suffix(".png")

    _print(f"[image] model={req.model} size={req.size} 源图={source_label}")
    _print(f"[image] prompt={args.prompt[:80]!r}")

    if source_input:
        resp = await client.generate_image(req, save_to=None)
        if resp.data:
            item = resp.data[0]
            if item.get("url"):
                await AgnesClient._download_to(item["url"], out_path)
            elif item.get("b64_json"):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                import base64
                out_path.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        resp = await client.generate_image(req, save_to=out_path if not args.base64 else None)
        if args.base64 and resp.data and resp.data[0].get("b64_json"):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            import base64
            out_path.write_bytes(base64.b64decode(resp.data[0]["b64_json"]))
        elif not out_path.exists() and resp.data:
            return_url = resp.data[0].get("url")
            _print(f"[image] 未下载,仅返回 URL: {return_url}")

    _print(f"[image] 已保存: {out_path}")
    log.append("image", {
        **{k: v for k, v in req.model_dump(exclude_none=True).items() if k != "image"},
        "image": source_label,
    }, {
        "path": str(out_path),
        "data": resp.data,
    })
    return 0


async def cmd_video(args: argparse.Namespace) -> int:
    settings = _build_settings()
    client = AgnesClient(settings)
    log = RunLog()

    extra_body: dict | None = None
    if args.keyframes and args.keyframes:
        extra_body = {"image": args.keyframes, "mode": "keyframes"}
    elif args.refs:
        extra_body = {"image": args.refs}

    req = VideoCreateRequest(
        prompt=args.prompt,
        image=args.image,
        mode=args.mode,
        height=args.height,
        width=args.width,
        num_frames=args.frames,
        frame_rate=args.fps,
        seed=args.seed,
        negative_prompt=args.negative,
        extra_body=extra_body,
    )

    out_path = Path(args.output)
    _print(
        f"[video] model={req.model} size={req.width}x{req.height} "
        f"frames={req.num_frames} fps={req.frame_rate}"
    )

    def on_progress(status: str | None, pct: int | None) -> None:
        _print(f"[video] 状态={status} 进度={pct}%")

    result = await client.generate_video(req, out_path, on_progress=on_progress)
    _print(f"[video] 已保存: {out_path}  ({result.seconds}s, {result.size})")
    log.append("video", req.model_dump(exclude_none=True), {
        "path": str(out_path),
        "video_url": result.video_url,
        "duration_sec": result.seconds,
        "size": result.size,
    })
    return 0


async def cmd_animate(args: argparse.Namespace) -> int:
    settings = _build_settings()
    client = AgnesClient(settings)
    log = RunLog()

    image_input: str | None = args.image
    image_label: str
    if args.image_file:
        _print(f"[animate] 读取本地图片: {args.image_file}")
        image_input = AgnesClient.local_image_to_data_uri(args.image_file)
        image_label = f"local:{args.image_file} (DataURI, {len(image_input)//1024} KB)"
    elif args.image:
        image_label = args.image
    else:
        print("[animate] 必须提供 --image (URL) 或 --image-file (本地路径)", file=sys.stderr)
        return 2

    req = VideoCreateRequest(
        prompt=args.prompt,
        image=image_input,
        height=args.height,
        width=args.width,
        num_frames=args.frames,
        frame_rate=args.fps,
    )

    out_path = Path(args.output)
    _print(f"[animate] 源图={image_label} prompt={args.prompt[:60]!r}")

    def on_progress(status: str | None, pct: int | None) -> None:
        _print(f"[animate] 状态={status} 进度={pct}%")

    result = await client.generate_video(req, out_path, on_progress=on_progress)
    _print(f"[animate] 已保存: {out_path}  ({result.seconds}s, {result.size})")
    log.append("animate", {
        **{k: v for k, v in req.model_dump(exclude_none=True).items() if k != "image"},
        "image": "(data-uri omitted from log)",
    }, {
        "path": str(out_path),
        "video_url": result.video_url,
    })
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    log = RunLog()
    for r in log.tail(args.n):
        params = r.get("params", {})
        prompt = str(params.get("prompt", ""))[:50]
        out = (r.get("result") or {}).get("path", "?")
        _print(f"{r['ts']}  {r['kind']:8s}  {out}  prompt={prompt!r}")
    return 0


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="auto_motion",
        description="Agnes AI 图像 & 视频生成实验脚手架",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_img = sub.add_parser("image", help="文生图 / 图生图")
    p_img.add_argument("prompt", help="文本提示")
    p_img.add_argument("--image", help="源图 URL(图生图模式)")
    p_img.add_argument("--image-file", help="本地源图路径(HEIC/JPG/PNG/WebP)")
    p_img.add_argument("--size", default="1152x768", help="输出尺寸,默认 1152x768")
    p_img.add_argument("--output", "-o", default="output/image.png", help="保存路径")
    p_img.add_argument("--base64", action="store_true", help="以 Base64 方式获取(图生图时不推荐)")
    p_img.set_defaults(func=cmd_image)

    p_vid = sub.add_parser("video", help="文生视频 / 多图视频 / 关键帧")
    p_vid.add_argument("prompt", help="视频内容描述")
    p_vid.add_argument("--image", help="单张源图 URL(可选,image-to-video 模式)")
    p_vid.add_argument("--refs", nargs="+", help="多张参考图 URL(走 extra_body.image)")
    p_vid.add_argument("--keyframes", nargs="+", help="关键帧 URL 列表(自动设置 mode=keyframes)")
    p_vid.add_argument("--mode", choices=["ti2vid", "keyframes"], help="显式模式")
    p_vid.add_argument("--width", type=int, default=1152)
    p_vid.add_argument("--height", type=int, default=768)
    p_vid.add_argument("--frames", type=int, default=121, help="总帧数,须 ≤441 且满足 8n+1")
    p_vid.add_argument("--fps", type=int, default=24, help="帧率 1-60")
    p_vid.add_argument("--seed", type=int)
    p_vid.add_argument("--negative", help="negative_prompt")
    p_vid.add_argument("--output", "-o", default="output/video.mp4")
    p_vid.set_defaults(func=cmd_video)

    p_ani = sub.add_parser("animate", help="图生视频(简化版,等价 video --image)")
    p_ani.add_argument("image", nargs="?", default=None, help="源图 URL(与 --image-file 二选一)")
    p_ani.add_argument("prompt", help="动作/运镜描述")
    p_ani.add_argument("--image-file", help="本地图片路径(HEIC/JPG/PNG/WebP),自动转 Data URI")
    p_ani.add_argument("--width", type=int, default=1152)
    p_ani.add_argument("--height", type=int, default=768)
    p_ani.add_argument("--frames", type=int, default=121)
    p_ani.add_argument("--fps", type=int, default=24)
    p_ani.add_argument("--output", "-o", default="output/animated.mp4")
    p_ani.set_defaults(func=cmd_animate)

    p_his = sub.add_parser("history", help="查看最近运行记录")
    p_his.add_argument("--n", type=int, default=10)
    p_his.set_defaults(func=cmd_history)

    args = parser.parse_args()
    if hasattr(args, "func"):
        code = asyncio.run(args.func(args))
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
