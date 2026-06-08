# auto_motion

> Agnes AI 图像 & 视频生成实验脚手架

基于 [Agnes AI](https://agnes-ai.com/doc/) 的图像与视频生成 API,做一个轻量的 CLI 工具,
快速跑通文生图、文生视频、图生视频、关键帧动画等实验。

## ✨ 特性

- **文生图** (`image`):使用 `agnes-image-2.1-flash`,支持自定义尺寸、URL/Base64 输出
- **文生视频** (`video`):使用 `agnes-video-v2.0`,异步任务轮询模式
- **图生视频** (`animate`):单图驱动的视频生成
- **多图/关键帧模式**:`video --refs` 或 `video --keyframes`
- **运行历史**:`history` 查看 `data/runs.jsonl`

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/hainingyu/Code/auto_motion
uv sync
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env,填入你的 AGNES_API_KEY
```

### 3. 运行

```bash
# 文生图
uv run python main.py image "a luminous floating city above a misty canyon at sunrise" \
    --size 1024x768 -o output/city.png

# 文生视频(约 5 秒)
uv run python main.py video "a cat walking on the beach at sunset, cinematic" \
    --width 1152 --height 768 --frames 121 --fps 24 \
    -o output/beach.mp4

# 图生视频(图需公网可访问 URL)
uv run python main.py animate "https://example.com/portrait.jpg" \
    "the woman slowly turns around and looks at the camera" \
    -o output/portrait.mp4

# 多图/关键帧
uv run python main.py video "smooth transition between keyframes" \
    --keyframes https://a.com/k1.png https://b.com/k2.png \
    -o output/transition.mp4

# 查看最近 10 次运行
uv run python main.py history --n 10
```

## 🧱 项目结构

```
auto_motion/
├── main.py             # CLI 入口(image/video/animate/history)
├── src/
│   ├── config.py       # .env 加载 + 配置
│   ├── client.py       # AgnesClient(图像/视频/异步轮询)
│   ├── models.py       # Pydantic 请求/响应模型
│   └── log.py          # 运行历史 (data/runs.jsonl)
├── tests/              # 冒烟测试
├── data/               # 运行历史
├── output/             # 生成的图像/视频
├── pyproject.toml
├── .env.example
├── README.md
└── CLAUDE.md
```

## ⚠️ Agnes API 关键约束

- **图像生成**:
  - ✅ 必填:`model`、`prompt`、`size`
  - ⚠️ `response_format` 放 `extra_body.response_format`,**不要**放顶层
  - ⚠️ 图生图用顶层 `image: []`,**不要**传 `tags: ["img2img"]`
- **视频生成**:
  - ✅ 异步任务:先 `POST /v1/videos` → 拿 `video_id` → `GET /agnesapi?video_id=...` 轮询
  - ⚠️ `num_frames` 必须 **≤441 且满足 `8n+1`** 规则(如 81/121/161/241/441)
  - ⚠️ `frame_rate` 范围 1-60
  - ⚠️ 客户端超时建议 60-360s
- **API Key 安全**:
  - 严禁提交到 git(`.env` 已在 `.gitignore`)
  - 仅在 `.env` 或环境变量中配置

## 🧪 测试

```bash
uv run pytest tests/
```

## 📚 参考

- [Agnes AI 调研报告](../docs/api/Agnes_AI_API_Report.md)
- [Agnes AI 官方文档](https://agnes-ai.com/doc/)
