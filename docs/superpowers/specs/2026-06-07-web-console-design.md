# auto_motion Web 控制台 — 设计文档

## 概述

为 auto_motion CLI 工具添加一个极简的本地 Web 界面，通过浏览器提供图像/视频生成能力，复用现有 `src/` 下的客户端代码。

## 技术选型

- **后端框架**: Flask（+ Jinja2 模板引擎）
- **新增依赖**: 仅 `flask`
- **运行方式**: `uv run python web.py`
- **重用的现有代码**: `src/client.py`、`src/config.py`、`src/models.py`
- **环境变量**: `AGNES_API_KEY`（必填）、`SENSENOVA_API_KEY`（sensenova 模型需填）

选型理由：本项目已用 Python + httpx，Flask 是零摩擦的轻量 Web 框架；Jinja2 为 Flask 内置；同步阻塞在桌面工具场景下不是问题。

## 架构

```
浏览器 (index.html)
  │
  ├─ POST /api/image         → web.py
  │   ├─ agnes-*             → src.client.AgnesClient.generate_image()
  │   └─ sensenova-u1-fast   → POST token.sensenova.cn/v1/images/generations
  ├─ POST /api/video         → web.py  ← 返回 task_id
  └─ GET  /api/video/<id>    → web.py  ← 前端轮询状态
          │
          ├─ src.config.Settings   (.env → AGNES_API_KEY / SENSENOVA_API_KEY)
          ├─ src.client.AgnesClient
          │   ├─ generate_image()
          │   ├─ create_video_task()
          │   └─ query_video()
          │
          ├─ sensenova-6.7-flash-lite  (prompt expansion via /v1/chat/completions)
          │
          └─ output/              (Flask static mount)
              ├── <file>.png
              └── <file>.mp4
```

## 文件结构

```
auto_motion/
├── web.py                  # [新建] Flask 应用 + 路由
├── templates/
│   └── index.html          # [新建] 单页面 UI
└── (其余全部复用现有)
```

## API 路由

| 方法 | 路径 | 输入 | 输出 | 说明 |
|---|---|---|---|---|
| GET | `/` | — | HTML | 渲染首页 |
| POST | `/api/image` | `{prompt, model, size, image?, expand_prompt?}` | `{url, local_path}` | 调用 Agnes 或 SenseNova API → 下载到 output/ → 返回本地路径 |
| POST | `/api/video` | `{prompt, model, width, height, frames, fps, seed?, negative_prompt?}` | `{task_id}` | 创建任务，不等待完成 |
| GET | `/api/video/<task_id>` | — | `{status, progress, url?, local_path?}` | 查询视频状态，前端轮询 |
| — | `/output/<path>` | — | 静态文件 | Flask 挂载 output/ 目录 |

### SenseNova 模型

| 模型 | 用途 | 端点 | 说明 |
|---|---|---|---|
| `sensenova-u1-fast` | 图像生成 | `POST /v1/images/generations` | 11 种固定尺寸，不支持图生图，不支持 Chat Completions |
| `sensenova-6.7-flash-lite` | 提示词扩写 | `POST /v1/chat/completions` | OpenAI 兼容，可选启用 |

### sensenova-u1-fast 支持尺寸

| 尺寸 | 宽高比 |
|---|---|
| `1664x2496` | 2:3 |
| `2496x1664` | 3:2 |
| `1760x2368` | 3:4 |
| `2368x1760` | 4:3 |
| `1824x2272` | 4:5 |
| `2272x1824` | 5:4 |
| `2048x2048` | 1:1 |
| `2752x1536` | 16:9（默认） |
| `1536x2752` | 9:16 |
| `3072x1376` | 21:9 |
| `1344x3136` | 9:21 |

> 尺寸是 2K 分辨率常量，非自由输入。Agnes 模型则使用自由尺寸如 `1152x768`。

## 数据流

### 图像生成（同步）
1. 前端 POST `/api/image` 带参数（model, prompt, size, expand_prompt）
2. 若 `expand_prompt=true` 且 `SENSENOVA_API_KEY` 已配置 → 调用 `sensenova-6.7-flash-lite` 扩写提示词
3. 按 model 路由：
   - `agnes-*` → `AgnesClient.generate_image()`
   - `sensenova-u1-fast` → `POST /v1/images/generations`
4. 返回的 URL 下载到 `output/{ts}-{uuid}.png`
5. 返回 `{url: "/output/xxx.png"}` 给前端
6. 前端 `<img>` 展示

### 视频生成（异步 + 前端轮询）
1. 前端 POST `/api/video` 带参数
2. web.py 调用 `AgnesClient.create_video_task()`
3. 返回 `{task_id}` 给前端
4. 前端每 5s GET `/api/video/{task_id}`
5. web.py 调用 `AgnesClient.query_video()`
6. 状态为 completed → 下载视频到 `output/`
7. 返回 `{status: "completed", progress: 100, url: "/output/xxx.mp4"}`
8. 前端 `<video>` 展示

## 前端 UI 设计

单页面，两张独立功能卡片，垂直排列：

### 图像生成卡片
- 模型选择下拉框（`agnes-image-2.1-flash` / `sensenova-u1-fast`）
- 提示词 textarea
- 尺寸输入（默认 `1152x768`；切到 `sensenova-u1-fast` 时提示 11 种固定尺寸）
- 源图 URL 输入（可选，仅 Agnes 支持；填了则图生图）
- 提示词扩写勾选框（可选，使用 `sensenova-6.7-flash-lite`）
- 生成按钮
- 结果预览区（`<img>`）

### 视频生成卡片
- 模型选择下拉框（默认 `agnes-video-v2.0`）
- 提示词 textarea
- 宽/高/帧数/帧率 输入
- Seed（可选）
- 反向提示词（可选）
- 生成按钮
- 进度条（轮询期间更新）
- 结果预览区（`<video controls>`）

### 通用
- 生成中显示 loading 状态，按钮禁用
- 错误在页面内显示（非 alert）
- 结果可点击下载

## 错误处理

- API Key 未配置：启动时直接退出，打印提示
- API 调用失败：路由内 try/except，返回 JSON `{error: "..."}`，前端展示
- 网络超时：Flask 侧复用客户端已有重试逻辑（`_post/_get` 内 3 次重试）

## 待办

- 添加 `.superpowers/` 到 `.gitignore`
- `web.py` 入口：`if __name__ == "__main__": app.run(debug=True, port=5000)`
