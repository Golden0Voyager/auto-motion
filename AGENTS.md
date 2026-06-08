# AGENTS.md — auto_motion

查看 `CLAUDE.md` 获取完整项目指南。以下仅补充易遗漏的要点。

## 最大陷阱

- `response_format` 必须放在 `extra_body` 里传递（`extra_body={"response_format": "url"}`），**不能**放顶层 payload — 违反会静默失败
- `num_frames` 必须 ≤441 **且**满足 `(n-1) % 8 == 0`（如 81, 121, 161, 241, 441）
- `sensenova-u1-fast` 使用 `POST /v1/images/generations`（**不是** `/v1/chat/completions`），**不能**传 `messages` 或 `n>1`
- `sensenova-u1-fast` 仅支持 11 种 2K 固定尺寸，不可自由输入；默认 `2752x1536`；列表：`1664x2496`, `2496x1664`, `1760x2368`, `2368x1760`, `1824x2272`, `2272x1824`, `2048x2048`, `2752x1536`, `1536x2752`, `3072x1376`, `1344x3136`
- `sensenova-6.7-flash-lite` 通过标准 `POST /v1/chat/completions` 调用，OpenAI SDK 兼容

## 架构细节

- 所有 CLI 命令通过 `asyncio.run(args.func(args))` 执行 — 无单独的异步入口
- `cli()` 是 `auto-motion` console_scripts 入口（在 `main.py` 中），但所有文档/示例用 `uv run python main.py ...`
- `RunLog` 是纯 JSONL 文件 (`data/runs.jsonl`)，非数据库 — `tail(n)` 读最后 n 行，无索引
- `query_video()` 走 `{host}/agnesapi?video_id=...`（非标准 REST），`query_video_legacy()` 回退 `{base_url}/videos/{id}`

## macOS 本地图片约束

- `local_image_to_data_uri()` 依赖 macOS `sips` 做 HEIC/非-PNG 转换 — Linux/Windows 上报错
- 转换逻辑压缩到 `max_side=768px`

## 测试约束

- `tests/` 仅冒烟 — 无 mock、无网络、无需 API Key
- 测试不覆盖 CLI 解析、客户端网络、异步逻辑
- 运行：`uv run pytest tests/`

## 代码规范

- 强制的 Type Hints（PEP 484），无注释（除非用户要求）
- 无配置的格式化/检查器（`ruff`、`black` 等项目中没有）— 不假设存在 lint 命令
- 无 CI/CD — 所有验证手动运行

## 端口/构建

- `pyproject.toml` 定义 `auto-motion` CLI 入口，但无 Docker / 部署配置
- 构建系统为 hatchling，包为 `src/` 下的命名空间
