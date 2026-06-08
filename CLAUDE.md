# CLAUDE.md — auto_motion

> Agnes AI 图像 & 视频生成实验脚手架

## ⚠️ 环境约束(强制)

- **包管理器**:`uv`(`uv sync` / `uv pip install ...`),禁止 `pip` / `python -m pip`
- **运行脚本**:`uv run python <script>.py` / `uv run python main.py ...`,禁止直接 `python`
- **API Key**:仅通过 `.env` 读取,**严禁**写入代码或提交到 git
- **代码风格**:Type Hints (PEP 484) 强制;**不加注释**,除非用户明确要求
- **错误处理**:所有 API 调用必须显式捕获并给出可读错误信息

---

## 项目概述

`auto_motion` 是 Agnes AI 多模态 API(图像/视频)的极简 CLI 实验工具。

- 目的:快速跑通文生图、文生视频、图生视频、关键帧动画等场景
- 非目的:不做工作流编排、不做画廊前端、不做批量调度

## 🧱 架构

```
main.py (CLI 解析,asyncio.run)
  └─ AgnesClient (src/client.py)
      ├─ generate_image()        POST /v1/images/generations
      ├─ create_video_task()     POST /v1/videos
      ├─ query_video()           GET  /agnesapi?video_id=...
      └─ generate_video()        异步轮询封装
  ├─ Settings (src/config.py)   读 .env
  ├─ Pydantic Models            强类型请求/响应
  └─ RunLog (src/log.py)        data/runs.jsonl
```

## 🚀 常用命令

```bash
uv sync                              # 安装依赖
uv run python main.py image ...      # 文生图
uv run python main.py video ...      # 文生视频(异步)
uv run python main.py animate ...    # 图生视频
uv run python main.py history        # 运行历史
uv run pytest tests/                 # 冒烟测试
```

## 🎯 模型规格(Agnes AI 当前主力)

| 模型 | 接口 | 关键约束 |
|---|---|---|
| `agnes-image-2.1-flash` | `POST /v1/images/generations` | `response_format` 必须放 `extra_body`;图生图用顶层 `image` |
| `agnes-video-v2.0` | `POST /v1/videos` (异步) | `num_frames ≤ 441` 且满足 `8n+1`;`frame_rate 1-60` |

详细参数与最佳实践见 `/Users/hainingyu/Code/docs/api/Agnes_AI_API_Report.md`。

## 📁 目录约定

- `output/` — 生成的图像/视频(被 gitignore)
- `data/runs.jsonl` — 运行历史(被 gitignore)
- `.scratch/` — 临时实验记录(被 gitignore)
- `tests/` — 冒烟测试,只验证模型/规则,不打网络

## 🔐 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `AGNES_API_KEY` | ✅ | 从 [Agnes AI 控制台](https://agnes-ai.com/) 申请 |
| `AGNES_BASE_URL` | ❌ | 默认 `https://apihub.agnes-ai.com/v1` |

## 🚫 严禁

- 读取/修改/提交 `.env`(含真实 Key)
- 把 API Key 写入代码、注释、文档
- 跨项目共享本目录代码
- 在 `output/` 之外存放大体积生成文件

## 🧹 项目卫生

- `uv run --with ...` 跑临时实验,**不要**持久化到 `pyproject.toml` 除非确定要保留
- 添加新功能前,先想清楚是否值得加进 `main.py` 子命令,避免 main.py 膨胀
- 客户端逻辑加在 `src/client.py`,不要散落在 `main.py`

---

## 🔭 后续可扩展方向(尚未实现,留作 .scratch/ 记录)

- 批量 prompt 队列与并发控制
- 图像 → 多段视频的关键帧流水线
- 视频拼接(`ffmpeg` 包装)
- 简单的 Web 画廊(本地 `index.html`)
- 引入 `Pillow` 做本地图像处理
