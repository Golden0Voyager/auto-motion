# Web 控制台 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 auto_motion 添加本地 Web 控制台（Flask + 单页面 UI），复用现有 `src/` 客户端代码。

**Architecture:** Flask 服务器 (`web.py`) 代理 Agnes API 请求，图像/视频结果下载到 `output/` 后通过 Flask 静态文件服务提供给前端。视频采用前端轮询模式。

**Tech Stack:** Flask, Jinja2, httpx, Pydantic

---

### Task 1: 添加 .superpowers/ 到 .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 追加 `.superpowers/` 到 `.gitignore`**

```gitignore
# .gitignore 末尾追加
.superpowers/
```

---

### Task 2: 添加 flask 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 在 `dependencies` 中添加 `flask`**

```toml
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "python-dotenv>=1.0.0",
    "flask>=3.0.0",
]
```

- [ ] **Step 2: 安装依赖**

```bash
uv sync
```

---

### Task 3: 创建 web.py — Flask 服务器

**Files:**
- Create: `web.py`

包含路由：
- `GET /` → 渲染 `index.html`
- `POST /api/image` → 同步生图，下载到 `output/`，返回本地 URL
- `POST /api/video` → 创建视频任务，返回 `{task_id}`
- `GET /api/video/<task_id>` → 查询视频状态，完成时下载到 `output/` 并返回 URL

- [ ] **Step 1: 创建 `web.py`**

```python
from __future__ import annotations

import asyncio
import base64
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from src.client import AgnesClient
from src.config import Settings
from src.models import ImageRequest, VideoCreateRequest

app = Flask(__name__)

OUTPUT_DIR = Path("output")


def _get_client() -> AgnesClient:
    settings = Settings.from_env()
    return AgnesClient(settings)


def _download_and_save(url: str, suffix: str = ".png") -> str:
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}-{uuid.uuid4().hex[:8]}{suffix}"
    dest = OUTPUT_DIR / filename
    asyncio.run(AgnesClient._download_to(url, dest))
    return f"/output/{filename}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/image", methods=["POST"])
def api_image():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "缺少 prompt"}), 400

    settings = Settings.from_env()
    client = AgnesClient(settings)

    extra_body = {"response_format": "url"}
    req = ImageRequest(
        prompt=data["prompt"],
        size=data.get("size", "1152x768"),
        model=data.get("model", "agnes-image-2.1-flash"),
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

    try:
        task = asyncio.run(client.create_video_task(req))
        video_id = task.video_id or task.task_id
        if not video_id:
            return jsonify({"error": "API 未返回 task_id"}), 502
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
```

---

### Task 4: 创建 templates/index.html — 前端页面

**Files:**
- Create: `templates/index.html`

单页面，两张功能卡片（生图 + 生视频）。使用纯 CSS（无框架），vanilla JS。

- [ ] **Step 1: 创建 `templates/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>auto_motion Web 控制台</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 24px; }
.container { max-width: 800px; margin: 0 auto; }
h1 { font-size: 24px; font-weight: 600; margin-bottom: 24px; }
.card { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.card h2 { font-size: 18px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #e8e8ed; }
.form-group { margin-bottom: 12px; }
label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; color: #6e6e73; }
input, textarea, select { width: 100%; padding: 8px 12px; border: 1px solid #d2d2d7; border-radius: 8px; font-size: 14px; font-family: inherit; }
textarea { min-height: 60px; resize: vertical; }
input:focus, textarea:focus, select:focus { outline: none; border-color: #0071e3; box-shadow: 0 0 0 3px rgba(0,113,227,0.2); }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #0071e3; color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; }
.btn:hover { background: #0077ed; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-group { display: flex; justify-content: flex-end; margin-top: 16px; }
.result-area { margin-top: 16px; padding: 16px; background: #f5f5f7; border-radius: 8px; min-height: 100px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.result-area img, .result-area video { max-width: 100%; max-height: 400px; border-radius: 8px; }
.result-area .loading { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #6e6e73; font-size: 14px; }
.spinner { width: 24px; height: 24px; border: 3px solid #e8e8ed; border-top-color: #0071e3; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { color: #ff3b30; font-size: 14px; padding: 8px; }
.hidden { display: none !important; }
.progress-bar { width: 100%; height: 6px; background: #e8e8ed; border-radius: 3px; overflow: hidden; margin: 8px 0; }
.progress-bar-fill { height: 100%; background: #0071e3; border-radius: 3px; transition: width 0.3s; }
</style>
</head>
<body>
<div class="container">
  <h1>🎬 auto_motion Web 控制台</h1>

  <div class="card">
    <h2>🖼️ 图像生成</h2>
    <div class="form-group">
      <label>模型</label>
      <select id="img-model">
        <option value="agnes-image-2.1-flash">agnes-image-2.1-flash</option>
      </select>
    </div>
    <div class="form-group">
      <label>提示词</label>
      <textarea id="img-prompt" placeholder="输入图像描述..."></textarea>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>尺寸</label>
        <input id="img-size" value="1152x768">
      </div>
      <div class="form-group">
        <label>源图 URL (可选，填了则图生图)</label>
        <input id="img-source" placeholder="留空则文生图">
      </div>
    </div>
    <div class="btn-group">
      <button class="btn" id="img-btn">🔄 生成图像</button>
    </div>
    <div id="img-result" class="result-area hidden"></div>
  </div>

  <div class="card">
    <h2>🎬 视频生成</h2>
    <div class="form-group">
      <label>模型</label>
      <select id="vid-model">
        <option value="agnes-video-v2.0">agnes-video-v2.0</option>
      </select>
    </div>
    <div class="form-group">
      <label>提示词</label>
      <textarea id="vid-prompt" placeholder="输入视频描述..."></textarea>
    </div>
    <div class="form-row">
      <div class="form-group"><label>宽</label><input id="vid-width" value="1152" type="number"></div>
      <div class="form-group"><label>高</label><input id="vid-height" value="768" type="number"></div>
      <div class="form-group"><label>帧数</label><input id="vid-frames" value="121" type="number"></div>
      <div class="form-group"><label>帧率</label><input id="vid-fps" value="24" type="number"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Seed (可选)</label><input id="vid-seed" placeholder="留空随机" type="number"></div>
      <div class="form-group"><label>反向提示 (可选)</label><input id="vid-negative" placeholder="可选"></div>
    </div>
    <div class="btn-group">
      <button class="btn" id="vid-btn">🔄 生成视频</button>
    </div>
    <div id="vid-result" class="result-area hidden"></div>
  </div>
</div>

<script>
async function api(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
  return data;
}

// === 图像 ===
const imgBtn = document.getElementById("img-btn");
const imgResult = document.getElementById("img-result");

imgBtn.addEventListener("click", async () => {
  imgResult.classList.remove("hidden");
  imgResult.innerHTML = `<div class="loading"><div class="spinner"></div><span>生成中...</span></div>`;
  imgBtn.disabled = true;

  try {
    const data = await api("/api/image", {
      prompt: document.getElementById("img-prompt").value,
      size: document.getElementById("img-size").value,
      model: document.getElementById("img-model").value,
      image: document.getElementById("img-source").value || null,
    });
    imgResult.innerHTML = `<img src="${data.url}" alt="生成结果">`;
  } catch (e) {
    imgResult.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
  } finally {
    imgBtn.disabled = false;
  }
});

// === 视频 ===
const vidBtn = document.getElementById("vid-btn");
const vidResult = document.getElementById("vid-result");

vidBtn.addEventListener("click", async () => {
  vidResult.classList.remove("hidden");
  vidResult.innerHTML = `<div class="loading"><div class="spinner"></div><span>创建任务中...</span></div>`;
  vidBtn.disabled = true;

  try {
    const task = await api("/api/video", {
      prompt: document.getElementById("vid-prompt").value,
      model: document.getElementById("vid-model").value,
      width: parseInt(document.getElementById("vid-width").value),
      height: parseInt(document.getElementById("vid-height").value),
      frames: parseInt(document.getElementById("vid-frames").value),
      fps: parseInt(document.getElementById("vid-fps").value),
      seed: document.getElementById("vid-seed").value ? parseInt(document.getElementById("vid-seed").value) : null,
      negative_prompt: document.getElementById("vid-negative").value || null,
    });

    vidResult.innerHTML = `
      <div class="loading" id="vid-polling">
        <div class="spinner"></div>
        <span id="vid-status-text">处理中...</span>
        <div class="progress-bar"><div class="progress-bar-fill" id="vid-progress" style="width:0%"></div></div>
      </div>`;

    const pollInterval = 3000;
    const maxAttempts = 120;
    let attempts = 0;

    const poll = setInterval(async () => {
      attempts++;
      try {
        const resp = await fetch(`/api/video/${task.task_id}`);
        const state = await resp.json();
        if (!resp.ok) throw new Error(state.error || `HTTP ${resp.status}`);

        const statusText = document.getElementById("vid-status-text");
        const progressFill = document.getElementById("vid-progress");
        if (statusText) statusText.textContent = state.status === "completed" ? "已完成" : `处理中 (${state.progress || 0}%)`;
        if (progressFill) progressFill.style.width = `${state.progress || 0}%`;

        if (state.status === "completed" && state.url) {
          clearInterval(poll);
          vidResult.innerHTML = `<video src="${state.url}" controls></video>`;
        } else if (state.status === "failed") {
          clearInterval(poll);
          vidResult.innerHTML = `<div class="error-msg">❌ 视频生成失败: ${state.error || "未知错误"}</div>`;
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          vidResult.innerHTML = `<div class="error-msg">❌ 轮询超时，请稍后查看</div>`;
        }
      } catch (e) {
        clearInterval(poll);
        vidResult.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
      }
    }, pollInterval);
  } catch (e) {
    vidResult.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
  } finally {
    vidBtn.disabled = false;
  }
});
</script>
</body>
</html>
```

---

### Task 5: 冒烟测试

**Files:**
- Create: `tests/test_web.py`

- [ ] **Step 1: 创建测试文件**

```python
from __future__ import annotations


def test_web_imports() -> None:
    from web import app
    assert app is not None
    assert app.name == "web"


def test_index_route() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert b"auto_motion" in resp.data
```

- [ ] **Step 2: 运行测试**

```bash
uv run pytest tests/test_web.py -v
```

输出：
```
tests/test_web.py::test_web_imports PASSED
tests/test_web.py::test_index_route PASSED
```

---

### Task 6: 运行全部冒烟测试验证

- [ ] **Step 1: 运行所有测试**

```bash
uv run pytest tests/ -v
```

输出预期：
```
tests/test_smoke.py::test_models_basic PASSED
tests/test_smoke.py::test_video_frames_rule PASSED
tests/test_web.py::test_web_imports PASSED
tests/test_web.py::test_index_route PASSED
```
