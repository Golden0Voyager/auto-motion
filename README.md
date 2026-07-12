# auto_motion

> Agnes AI 图像 & 视频生成实验脚手架

基于 [Agnes AI](https://agnes-ai.com/doc/) 的图像与视频生成 API,做一个轻量的 CLI 工具,
快速跑通文生图、文生视频、图生视频、关键帧动画等实验。

## ✨ 特性

- **文生图** (`image`):使用 `agnes-image-2.1-flash`,支持自定义尺寸、URL/Base64 输出
- **文生视频** (`video`):使用 `agnes-video-v2.0`,异步任务轮询模式
- **图生视频** (`animate`):单图驱动的视频生成
- **多图/关键帧模式**:`video --refs` 或 `video --keyframes`
- **通义千问文生图** (`qwen`):使用 `Qwen-Image-2.0`(scnet.cn),同步返回图像 URL 并自动下载
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

# HappyHorse 文生视频(更高画质,自带音频)
uv run python main.py happyhorse "晴朗的蓝天下一片白色雏菊花田" \
    --duration 5 --resolution 720p \
    -o output/happyhorse.mp4

# 万相文生视频(支持反向提示词/音频驱动)
uv run python main.py wan "一只金毛犬在海边奔跑，夕阳西下" \
    --duration 5 --resolution 720p \
    --negative-prompt "模糊,低质量" \
    -o output/wan.mp4

# 通义千问文生图(同步,自动下载;size 用 宽*高)
uv run python main.py qwen "清晨薄雾中的高山湖泊，写实摄影" \
    --size 1024*1024 \
    -o output/qwen_image.png

# 查看最近 10 次运行
uv run python main.py history --n 10
```

## 🧱 项目结构

```
auto_motion/
├── main.py             # CLI 入口(image/video/animate/history/seedance/happyhorse/wan/qwen)
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
- **scnet.cn 图像生成 (Qwen-Image-2.0)**:
  - ✅ 同步接口:`POST /images/generations`,直接返回图像 URL 并自动下载
  - ⚠️ `size` 用 `宽*高`(如 `1024*1024`),**不是** Agnes 的 `1024x768`;总像素需在 512²~2048² 之间
  - ⚠️ `n` 范围 1-6,超出会被截断到该区间
  - ⚠️ `prompt_extend` 默认开、`watermark` 默认关;`--no-prompt-extend` 可关闭扩展
  - ⚠️ 各模型有每日请求配额,超限返回 HTTP 433(显式捕获并打印)

## 🧪 测试

```bash
uv run pytest tests/
```

## 📚 参考

- [Agnes AI 调研报告](../docs/api/Agnes_AI_API_Report.md)
- [Agnes AI 官方文档](https://agnes-ai.com/doc/)
