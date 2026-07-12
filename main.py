from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from src.client import AgnesClient, SeedanceClient
from src.config import Settings
from src.log import RunLog
from src.models import (
    HappyHorseInput,
    HappyHorseParameters,
    HappyHorseRequest,
    ImageRequest,
    QwenImageInput,
    QwenImageParameters,
    QwenImageRequest,
    SeedanceInput,
    SeedanceMedia,
    SeedanceParameters,
    SeedanceRequest,
    VideoCreateRequest,
    WanInput,
    WanParameters,
    WanRequest,
)


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


async def cmd_seedance(args: argparse.Namespace) -> int:
    settings = _build_settings()
    if not settings.seedance_api_key:
        print("[配置错误] SEEDANCE_API_KEY 未配置", file=sys.stderr)
        return 2

    client = SeedanceClient(settings)
    log = RunLog()

    media: list[SeedanceMedia] | None = None
    if args.ref_image:
        media = [SeedanceMedia(type="reference_image", url=args.ref_image)]
    if args.ref_video:
        media = media or []
        media.append(SeedanceMedia(type="reference_video", url=args.ref_video))
    if args.ref_audio:
        media = media or []
        media.append(SeedanceMedia(type="reference_audio", url=args.ref_audio))

    input_data = SeedanceInput(
        prompt=args.prompt,
        media=media if media else None,
    )

    params = SeedanceParameters(
        generate_audio=args.audio,
        ratio=args.ratio,
        duration=args.duration,
        resolution=args.resolution,
        watermark=args.watermark,
        seed=args.seed,
        camera_fixed=args.camera_fixed,
    )

    req = SeedanceRequest(
        model=args.model,
        input=input_data,
        parameters=params,
    )

    out_path = Path(args.output)
    _print(f"[seedance] model={req.model} duration={params.duration}s ratio={params.ratio} res={params.resolution}")
    _print(f"[seedance] prompt={args.prompt[:80]!r}")

    def on_progress(status: str | None, pct: int | None) -> None:
        _print(f"[seedance] 状态={status}")

    result = await client.generate_video(req, out_path, on_progress=on_progress)

    video_url = result.output.results[0] if result.output and result.output.results else "unknown"
    usage_info = ""
    if result.usage and result.usage.video_duration:
        usage_info = f"  时长={result.usage.video_duration}s"

    _print(f"[seedance] 已保存: {out_path}{usage_info}")
    log.append("seedance", {
        "model": req.model,
        "prompt": args.prompt[:100],
        "duration": params.duration,
        "ratio": params.ratio,
        "resolution": params.resolution,
    }, {
        "path": str(out_path),
        "video_url": video_url,
        "task_id": result.output.task_id if result.output else None,
    })
    return 0


async def cmd_seedance_query(args: argparse.Namespace) -> int:
    settings = _build_settings()
    if not settings.seedance_api_key:
        print("[配置错误] SEEDANCE_API_KEY 未配置", file=sys.stderr)
        return 2

    client = SeedanceClient(settings)
    result = await client.query_task(args.task_id)

    _print(f"任务 ID: {result.output.task_id if result.output else 'N/A'}")
    _print(f"状态: {result.output.task_status if result.output else 'N/A'}")
    if result.output and result.output.results:
        _print(f"视频地址: {result.output.results[0]}")
    if result.output and result.output.error_message:
        _print(f"错误: {result.output.error_message}")
    if result.usage:
        _print(f"用量: {result.usage.model_dump()}")

    return 0


async def cmd_wan(args: argparse.Namespace) -> int:
    settings = _build_settings()
    if not settings.seedance_api_key:
        print("[配置错误] SEEDANCE_API_KEY 未配置", file=sys.stderr)
        return 2

    client = SeedanceClient(settings)
    log = RunLog()

    input_data = WanInput(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        audio_url=args.audio_url,
    )
    params = WanParameters(
        resolution=args.resolution,
        ratio=args.ratio,
        duration=args.duration,
        prompt_extend=args.prompt_extend if args.prompt_extend else None,
        watermark=args.watermark,
        seed=args.seed,
    )
    req = WanRequest(
        model=args.model,
        input=input_data,
        parameters=params,
    )

    out_path = Path(args.output)
    _print(f"[wan] model={req.model} duration={params.duration}s ratio={params.ratio} res={params.resolution}")
    _print(f"[wan] prompt={args.prompt[:80]!r}")

    def on_progress(status: str | None, pct: int | None) -> None:
        _print(f"[wan] 状态={status}")

    result = await client.generate_video(req, out_path, on_progress=on_progress)

    video_url = result.output.results[0] if result.output and result.output.results else "unknown"
    usage_info = ""
    if result.usage and result.usage.video_duration:
        usage_info = f"  时长={result.usage.video_duration}s"

    _print(f"[wan] 已保存: {out_path}{usage_info}")
    log.append("wan", {
        "model": req.model,
        "prompt": args.prompt[:100],
        "duration": params.duration,
        "ratio": params.ratio,
        "resolution": params.resolution,
    }, {
        "path": str(out_path),
        "video_url": video_url,
        "task_id": result.output.task_id if result.output else None,
    })
    return 0


async def cmd_happyhorse(args: argparse.Namespace) -> int:
    settings = _build_settings()
    if not settings.seedance_api_key:
        print("[配置错误] SEEDANCE_API_KEY 未配置", file=sys.stderr)
        return 2

    client = SeedanceClient(settings)
    log = RunLog()

    input_data = HappyHorseInput(prompt=args.prompt)
    params = HappyHorseParameters(
        resolution=args.resolution,
        ratio=args.ratio,
        duration=args.duration,
        watermark=args.watermark,
        seed=args.seed,
    )
    req = HappyHorseRequest(
        model=args.model,
        input=input_data,
        parameters=params,
    )

    out_path = Path(args.output)
    _print(f"[happyhorse] model={req.model} duration={params.duration}s ratio={params.ratio} res={params.resolution}")
    _print(f"[happyhorse] prompt={args.prompt[:80]!r}")

    def on_progress(status: str | None, pct: int | None) -> None:
        _print(f"[happyhorse] 状态={status}")

    result = await client.generate_video(req, out_path, on_progress=on_progress)

    video_url = result.output.results[0] if result.output and result.output.results else "unknown"
    usage_info = ""
    if result.usage and result.usage.video_duration:
        usage_info = f"  时长={result.usage.video_duration}s"

    _print(f"[happyhorse] 已保存: {out_path}{usage_info}")
    log.append("happyhorse", {
        "model": req.model,
        "prompt": args.prompt[:100],
        "duration": params.duration,
        "ratio": params.ratio,
        "resolution": params.resolution,
    }, {
        "path": str(out_path),
        "video_url": video_url,
        "task_id": result.output.task_id if result.output else None,
    })
    return 0


async def cmd_qwen(args: argparse.Namespace) -> int:
    settings = _build_settings()
    if not settings.seedance_api_key:
        print("[配置错误] SEEDANCE_API_KEY 未配置", file=sys.stderr)
        return 2

    client = SeedanceClient(settings)
    log = RunLog()

    size = args.size
    if args.width and args.height:
        size = f"{args.width}*{args.height}"

    input_data = QwenImageInput(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
    )
    params = QwenImageParameters(
        size=size,
        n=args.n,
        negative_prompt=args.negative_prompt,
        prompt_extend=args.prompt_extend,
        watermark=args.watermark,
        seed=args.seed,
    )
    req = QwenImageRequest(
        model=args.model,
        input=input_data,
        parameters=params,
    )

    out_path = Path(args.output)
    _print(f"[qwen] model={req.model} size={size} n={params.n} prompt_extend={params.prompt_extend}")
    _print(f"[qwen] prompt={args.prompt[:80]!r}")

    result = await client.generate_image(req, out_path)

    urls = result.output.results if result.output and result.output.results else []
    usage_info = ""
    if result.usage and result.usage.resolution:
        usage_info = f"  分辨率={result.usage.resolution} 张数={result.usage.image_count}"

    _print(f"[qwen] 已保存: {out_path}{usage_info}")
    log.append("qwen", {
        "model": req.model,
        "prompt": args.prompt[:100],
        "size": size,
        "n": params.n,
        "prompt_extend": params.prompt_extend,
    }, {
        "path": str(out_path),
        "urls": urls,
        "task_id": result.output.task_id if result.output else None,
    })
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

    p_seed = sub.add_parser("seedance", help="Seedance 视频生成(文生视频/多模态)")
    p_seed.add_argument("prompt", help="视频内容描述")
    p_seed.add_argument("--model", default="Seedance2.0", help="模型名称,默认 Seedance2.0")
    p_seed.add_argument("--ref-image", help="参考图 URL")
    p_seed.add_argument("--ref-video", help="参考视频 URL")
    p_seed.add_argument("--ref-audio", help="参考音频 URL")
    p_seed.add_argument("--audio", action="store_true", help="生成同步声音")
    p_seed.add_argument("--ratio", default="16:9", choices=["16:9", "9:16", "adaptive"], help="宽高比")
    p_seed.add_argument("--duration", type=int, default=5, help="视频时长(4-15秒)")
    p_seed.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"], help="分辨率")
    p_seed.add_argument("--watermark", action="store_true", help="添加水印")
    p_seed.add_argument("--seed", type=int, help="随机种子")
    p_seed.add_argument("--camera-fixed", action="store_true", help="固定摄像头")
    p_seed.add_argument("--output", "-o", default="output/seedance_video.mp4", help="保存路径")
    p_seed.set_defaults(func=cmd_seedance)

    p_sq = sub.add_parser("seedance-query", help="查询 Seedance 任务状态")
    p_sq.add_argument("task_id", help="任务 ID")
    p_sq.set_defaults(func=cmd_seedance_query)

    p_hh = sub.add_parser("happyhorse", help="HappyHorse 文生视频(HappyHorse-1.0-T2V)")
    p_hh.add_argument("prompt", help="视频内容描述")
    p_hh.add_argument("--model", default="HappyHorse-1.0-T2V", help="模型名称,默认 HappyHorse-1.0-T2V")
    p_hh.add_argument("--ratio", default="16:9",
                      choices=["16:9", "9:16", "1:1", "4:3", "3:4", "4:5", "5:4", "9:21", "21:9"],
                      help="宽高比")
    p_hh.add_argument("--duration", type=int, default=5, help="视频时长(3-15秒)")
    p_hh.add_argument("--resolution", default="720p", choices=["720p", "1080p"], help="分辨率")
    p_hh.add_argument("--watermark", action="store_true", dest="watermark", default=True, help="添加水印(默认添加)")
    p_hh.add_argument("--no-watermark", action="store_false", dest="watermark", help="不添加水印")
    p_hh.add_argument("--seed", type=int, help="随机种子")
    p_hh.add_argument("--output", "-o", default="output/happyhorse_video.mp4", help="保存路径")
    p_hh.set_defaults(func=cmd_happyhorse)

    p_wan = sub.add_parser("wan", help="万相文生视频(Wan2.7-T2V)")
    p_wan.add_argument("prompt", help="视频内容描述")
    p_wan.add_argument("--model", default="Wan2.7-T2V", help="模型名称,默认 Wan2.7-T2V")
    p_wan.add_argument("--negative-prompt", help="反向提示词")
    p_wan.add_argument("--audio-url", help="音频文件 URL(用于音频驱动视频)")
    p_wan.add_argument("--ratio", default="16:9", choices=["16:9", "9:16"], help="宽高比")
    p_wan.add_argument("--duration", type=int, default=5, help="视频时长(2-15秒)")
    p_wan.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"], help="分辨率")
    p_wan.add_argument("--prompt-extend", action="store_true", help="开启提示词扩展")
    p_wan.add_argument("--watermark", action="store_true", help="添加水印")
    p_wan.add_argument("--seed", type=int, help="随机种子")
    p_wan.add_argument("--output", "-o", default="output/wan_video.mp4", help="保存路径")
    p_wan.set_defaults(func=cmd_wan)

    p_qwen = sub.add_parser("qwen", help="通义千问文生图(Qwen-Image-2.0)")
    p_qwen.add_argument("prompt", help="图像描述")
    p_qwen.add_argument("--model", default="Qwen-Image-2.0", help="模型名称,默认 Qwen-Image-2.0")
    p_qwen.add_argument("--size", default="2048*2048", help="输出尺寸 宽*高,默认 2048*2048")
    p_qwen.add_argument("--width", type=int, help="与 --height 组合覆盖 --size")
    p_qwen.add_argument("--height", type=int, help="与 --width 组合覆盖 --size")
    p_qwen.add_argument("--n", type=int, default=1, help="生成数量 1-6")
    p_qwen.add_argument("--negative-prompt", help="反向提示词")
    p_qwen.add_argument("--no-prompt-extend", action="store_false", dest="prompt_extend",
                        help="关闭提示词扩展(默认开启)")
    p_qwen.add_argument("--watermark", action="store_true", help="添加水印")
    p_qwen.add_argument("--seed", type=int, help="随机种子")
    p_qwen.add_argument("--output", "-o", default="output/qwen_image.png", help="保存路径")
    p_qwen.set_defaults(func=cmd_qwen, prompt_extend=True)

    args = parser.parse_args()
    if hasattr(args, "func"):
        code = asyncio.run(args.func(args))
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
