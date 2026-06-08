from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, asdict
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
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")
SENSENOVA_BASE_URL = "https://token.sensenova.cn/v1"
SENSENOVA_VALID_SIZES = {
    "1664x2496", "2496x1664", "1760x2368", "2368x1760",
    "1824x2272", "2272x1824", "2048x2048",
    "2752x1536", "1536x2752", "3072x1376", "1344x3136",
}
SENSENOVA_DEFAULT_SIZE = "2752x1536"


@dataclass
class PromptTemplate:
    id: str
    category: str
    icon: str
    name: str
    desc: str
    template: str
    params: dict


CARD_TEMPLATES: list[PromptTemplate] = [
    PromptTemplate(
        id="portrait_01",
        category="人像摄影",
        icon="🧑",
        name="温暖光影肖像",
        desc="自然光下的环境人像，肤色通透、眼神生动",
        template="Close portrait of {subject}, textured skin, gentle smile, "
        "warm natural light, emotional documentary look. The portrait should feel "
        "polished and natural, with sharp eyes, realistic skin texture, accurate "
        "facial anatomy, and premium lighting that keeps the face as the main focus.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    PromptTemplate(
        id="portrait_02",
        category="人像摄影",
        icon="🧑",
        name="街头纪实",
        desc="都市环境中抓拍，真实情绪与质感",
        template="Documentary-style portrait of {subject} in an urban environment, "
        "natural light, candid moment, gritty texture, emotional realism, "
        "street photography aesthetic with sharp facial details.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    PromptTemplate(
        id="landscape_01",
        category="自然风光",
        icon="🌄",
        name="日落山川",
        desc="金色时刻的广阔山川，浪漫氛围",
        template="{subject} stretching to the horizon under a pastel sunset, "
        "highly detailed foreground, romantic countryside scene, golden hour "
        "lighting with soft warm tones, ultra-realistic depth.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
    PromptTemplate(
        id="landscape_02",
        category="自然风光",
        icon="🌄",
        name="风暴海岸",
        desc="戏剧化的海浪与天空，自然力量",
        template="Stormy seascape with {subject}, dramatic sky with dark clouds, "
        "realistic water motion and foam, moody coastal photography, "
        "ultra-detailed waves crashing against rocks.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
    PromptTemplate(
        id="cyberpunk_01",
        category="赛博朋克",
        icon="🌆",
        name="霓虹之夜",
        desc="霓虹闪烁的城市夜景，赛博朋克美学",
        template="A futuristic cyberpunk scene of {subject}, neon-lit cityscape, "
        "rain-slicked streets reflecting holographic billboards, "
        "purple and cyan lighting, cinematic composition, Blade Runner aesthetic.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
    PromptTemplate(
        id="infographic_01",
        category="信息图",
        icon="📊",
        name="科技报告风",
        desc="现代科技感的数据信息图",
        template="This infographic about {subject} uses a modern tech style. "
        "Clean grid layout, dark background with neon accent colors, "
        "data charts and diagrams, professional typography, high information density.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    PromptTemplate(
        id="watercolor_01",
        category="水彩插画",
        icon="🎨",
        name="清新手绘",
        desc="柔和水彩风格，梦幻清新的插画感",
        template="Watercolor illustration of {subject}, soft pastel colors, "
        "gentle brush strokes, artistic and dreamy style, white background "
        "with subtle paper texture, delicate details.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    PromptTemplate(
        id="retro_01",
        category="复古档案",
        icon="🏛️",
        name="旧纸档案",
        desc="做旧纸张质感，复古历史风格",
        template="Create an archival-style document about {subject} in sepia "
        "and parchment tones, distressed edges, vintage typography, "
        "historical aesthetic, aged paper texture, 19th century document feel.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    # --- 第二批次：美食摄影 ---
    PromptTemplate(
        id="food_01",
        category="美食摄影",
        icon="🍜",
        name="精致料理",
        desc="精致的摆盘与柔光，美食杂志质感",
        template="Plated {subject} on a ceramic plate, soft natural window lighting "
        "from the left, shallow depth of field, garnished with fresh herbs, "
        "fine dining presentation, warm neutral background, macro food photography, "
        "sharp focus on the main dish, creamy bokeh background, appetizing and vibrant.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    PromptTemplate(
        id="food_02",
        category="美食摄影",
        icon="🍜",
        name="烘焙甜点",
        desc="新鲜出炉的甜点面包，温暖治愈",
        template="{subject} fresh from the oven, steam rising gently, "
        "golden brown crust with delicate caramelization, rustic wooden table, "
        "soft morning light dusted with flour, warm and cozy bakery atmosphere, "
        "detailed texture close-up, tempting and delicious, homestyle comfort.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    # --- 第三批次：动漫风格 ---
    PromptTemplate(
        id="anime_01",
        category="动漫风格",
        icon="🌸",
        name="吉卜力田园",
        desc="宫崎骏动画风格的田园风景，温暖治愈",
        template="Studio Ghibli style illustration of {subject}, soft watercolor-inspired "
        "backgrounds, warm pastel colors, lush greenery, gentle sunlight filtering "
        "through leaves, whimsical and nostalgic atmosphere, hand-drawn anime aesthetic, "
        "detailed natural elements, Miyazaki-inspired, peaceful and dreamy.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
    # --- 第四批次：3D 渲染 ---
    PromptTemplate(
        id="render_01",
        category="3D 渲染",
        icon="🧸",
        name="皮克斯风格",
        desc="皮克斯/迪士尼风格 3D 角色，生动有趣",
        template="Pixar-style 3D render of {subject}, highly detailed character design, "
        "soft global illumination, vibrant saturated colors, volumetric lighting, "
        "subsurface scattering on skin, toy story aesthetic, smooth rounded surfaces, "
        "playful and expressive, cinematic depth of field, 8k quality render.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    # --- 第五批次：建筑空间 ---
    PromptTemplate(
        id="architecture_01",
        category="建筑空间",
        icon="🏛️",
        name="现代建筑",
        desc="极简主义建筑摄影，线条与光影之美",
        template="Modern architectural photography of {subject}, clean geometric lines, "
        "minimalist composition, natural light casting dramatic shadows, "
        "glass and concrete materials, blue hour sky, wide angle lens, "
        "sharp architectural details, Architectural Digest style, "
        "symmetrical framing, elegant urban design.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
    PromptTemplate(
        id="interior_01",
        category="建筑空间",
        icon="🏛️",
        name="温馨室内",
        desc="柔和光线的室内空间，北欧/日式氛围",
        template="Cozy interior design of {subject}, warm ambient lighting, "
        "natural materials like wood and linen, neutral color palette with "
        "accent plants, hygge atmosphere, soft shadows, inviting and peaceful, "
        "interior design magazine photography, clean uncluttered spaces.",
        params={"model": "sensenova-u1-fast", "size": "2048x2048"},
    ),
    # --- 第六批次：科幻太空 ---
    PromptTemplate(
        id="sci-fi_01",
        category="科幻太空",
        icon="🚀",
        name="深空探索",
        desc="宇宙深空场景，宏大壮丽的科幻美学",
        template="Epic sci-fi scene of {subject}, deep space background with "
        "colorful nebulae and distant stars, dramatic volumetric lighting, "
        "highly detailed spacecraft or cosmic structures, immense scale, "
        "cinematic composition, realistic physics-based rendering, "
        "awe-inspiring vista, Interstellar aesthetic.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
    # --- 第七批次：中国风 ---
    PromptTemplate(
        id="inkwash_01",
        category="中国风",
        icon="🖌️",
        name="水墨意境",
        desc="传统水墨画风格，留白与写意的东方美学",
        template="Traditional Chinese ink wash painting of {subject}, sumi-e style, "
        "loose flowing brushstrokes, black ink on rice paper with subtle gray washes, "
        "expressive negative space, poetic and minimalist composition, "
        "misty mountains or bamboo aesthetic, oriental elegance, hand-painted feel, "
        "artistic brushwork with ink bleeding effects.",
        params={"model": "sensenova-u1-fast", "size": "2752x1536"},
    ),
]


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
    except Exception as e:
        logger.warning("prompt 扩写失败: %s", e)
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


@app.route("/api/templates")
def api_templates():
    return jsonify({"templates": [asdict(t) for t in CARD_TEMPLATES]})


@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    data = request.get_json()
    if not data or not data.get("subject", "").strip():
        return jsonify({"error": "缺少 subject"}), 400

    settings = Settings.from_env()
    subject = data["subject"].strip()
    template_id = data.get("template_id")
    custom_prompt = data.get("custom_prompt")

    # 选择模版或使用自定义 prompt
    if custom_prompt:
        final_prompt = custom_prompt
        params = {"model": "sensenova-u1-fast", "size": "2048x2048"}
    elif template_id:
        tpl = next((t for t in CARD_TEMPLATES if t.id == template_id), None)
        if not tpl:
            return jsonify({"error": f"模版 {template_id} 不存在"}), 400
        final_prompt = tpl.template.replace("{subject}", subject)
        params = dict(tpl.params)
    else:
        final_prompt = subject
        params = {"model": "sensenova-u1-fast", "size": "2048x2048"}

    # 允许用户覆盖 model / size
    if data.get("model"):
        params["model"] = data["model"]
    if data.get("size"):
        params["size"] = data["size"]

    # Step 1: 扩写
    expanded = final_prompt
    try:
        expanded = asyncio.run(_expand_prompt(settings, final_prompt))
    except Exception as e:
        logger.warning("扩写阶段出错，使用原 prompt: %s", e)

    # Step 2+3: 生成图像
    try:
        size = params.get("size", "2048x2048")
        image_url = asyncio.run(_sensenova_generate_image(settings, expanded, size))
        local_path = _download_and_save(image_url, ".png")
        return jsonify({
            "original": subject,
            "expanded": expanded,
            "params": params,
            "url": local_path,
            "original_url": image_url,
            "model_used": params["model"],
        })
    except RuntimeError as e:
        return jsonify({
            "error": f"图像生成失败: {e}",
            "expanded": expanded,
            "step": "generating",
        }), 502
    except Exception as e:
        return jsonify({
            "error": f"未知错误: {e}",
            "expanded": expanded,
            "step": "generating",
        }), 502


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
