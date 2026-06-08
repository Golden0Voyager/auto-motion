# 智能抽卡优化 — 设计规格

> 在 auto_motion Web 控制台中新增「智能抽卡」功能，提供预制提示词模版 + 逐步骤可视化优化体验。
> **创建日期**: 2026-06-08
> **分支**: `feat/prompt-card-drawing`

---

## 1. 概述

### 1.1 目标

在现有 Web 控制台中集成「智能抽卡」面板，用户可通过预制模版或自由输入，实时观看提示词从扩写→调参→生成的完整过程，提升图像生成的质量和趣味性。

### 1.2 核心流程

```
选模版/输入 ──→ Step 1: 扩写 ──→ Step 2: 参数配置 ──→ Step 3: 生成 ──→ Step 4: 结果
                (sensenova-6.7    (自动推荐          (sensenova-u1-fast)  (展示+下载+
                 -flash-lite)      model+size)                           重新抽卡)
```

### 1.3 非目标

- 不做 SSE 实时推送，统一为同步请求+前端动画模拟
- 不做 CLI 支持，仅限 Web 控制台
- 不做模板编辑/保存功能

---

## 2. 模版系统

### 2.1 数据结构

```python
@dataclass
class PromptTemplate:
    id: str                    # 唯一标识，如 "portrait_01"
    category: str              # 分类名，如 "人像摄影"
    icon: str                  # emoji 图标
    name: str                  # 展示名
    desc: str                  # 简短描述
    template: str              # 提示词骨架，含 {subject} 占位符
    params: dict               # 推荐参数 {model, size}
```

### 2.2 初始模版清单（8 个）

#### 🧑 人像摄影

| ID | 名称 | 模板 prompt | 推荐参数 |
|----|------|------------|---------|
| portrait_01 | 温暖光影肖像 | "Close portrait of {subject}, textured skin, gentle smile, warm natural light, emotional documentary look..." | u1-fast, 2048x2048 |
| portrait_02 | 街头纪实 | "Documentary-style portrait of {subject} in an urban environment, natural light, candid moment, gritty texture, emotional realism." | u1-fast, 2048x2048 |

#### 🌄 自然风光

| ID | 名称 | 模板 prompt | 推荐参数 |
|----|------|------------|---------|
| landscape_01 | 日落山川 | "{subject} stretching to the horizon under a pastel sunset, highly detailed, romantic countryside scene, golden hour lighting." | u1-fast, 2752x1536 |
| landscape_02 | 风暴海岸 | "Stormy seascape with {subject}, dramatic sky, realistic water motion, moody coastal photography, ultra-detailed waves." | u1-fast, 2752x1536 |

#### 🌆 赛博朋克

| ID | 名称 | 模板 prompt | 推荐参数 |
|----|------|------------|---------|
| cyberpunk_01 | 霓虹之夜 | "A neon-lit {subject} in a cyberpunk cityscape, rain-slicked streets, holographic billboards, purple and cyan lighting, cinematic." | u1-fast, 2752x1536 |

#### 📊 信息图

| ID | 名称 | 模板 prompt | 推荐参数 |
|----|------|------------|---------|
| infographic_01 | 科技报告风 | "This infographic about {subject} uses a modern tech style. Clean grid layout, dark background with neon accent colors, data charts..." | u1-fast, 2048x2048 |

#### 🎨 水彩插画

| ID | 名称 | 模板 prompt | 推荐参数 |
|----|------|------------|---------|
| watercolor_01 | 清新手绘 | "Watercolor illustration of {subject}, soft pastel colors, gentle brush strokes, artistic and dreamy style, white background with subtle paper texture." | u1-fast, 2048x2048 |

#### 🏛️ 复古档案

| ID | 名称 | 模板 prompt | 推荐参数 |
|----|------|------------|---------|
| retro_01 | 旧纸档案 | "Create an archival-style document about {subject} in sepia and parchment tones, distressed edges, vintage typography, historical aesthetic." | u1-fast, 2048x2048 |

---

## 3. API 设计

### 3.1 GET /api/templates

返回所有预制模版。

**Response 200**:
```json
{
  "templates": [
    {
      "id": "portrait_01",
      "category": "人像摄影",
      "icon": "🧑",
      "name": "温暖光影肖像",
      "desc": "自然光下的环境人像...",
      "template": "Close portrait of {subject}, ...",
      "params": {"model": "sensenova-u1-fast", "size": "2048x2048"}
    },
    ...
  ]
}
```

### 3.2 POST /api/optimize

接受用户输入 + 可选模版，执行完整扩写→生成流水线，返回所有步骤结果。

**Request**:
```json
{
  "template_id": "portrait_01",
  "subject": "a young woman with freckles",
  "custom_prompt": null
}
```

**Response 200**:
```json
{
  "original": "a young woman with freckles",
  "expanded": "Close portrait of a young woman with freckles...",
  "params": {"model": "sensenova-u1-fast", "size": "2048x2048"},
  "url": "/output/xxx.png",
  "original_url": "https://cdn...",
  "model_used": "sensenova-u1-fast"
}
```

**Error Response** (扩写/生成任一失败):
```json
{
  "error": "图像生成失败: SenseNova API 返回 429 (配额用尽)",
  "expanded": "Close portrait of ...",     // 扩写可能成功
  "step": "generating"                     // 失败步骤标识
}
```

### 3.3 后端实现要点

- 复用 `_sensenova_generate_image()` 和 `_expand_prompt()` (web.py 已有)
- `/api/optimize` 用 `try/except` 分别捕获扩写阶段和生成阶段的错误
- 模版列表以 Python 常量列表定义在 `web.py` 中，不引入数据库

---

## 4. 前端实现

### 4.1 页面布局

在 `templates/index.html` 的图像生成卡片和视频生成卡片之间插入新卡片：

```
<div class="card">
  <h2>🎴 智能抽卡</h2>
  <!-- ① 模版选择区 -->
  <div id="card-templates">
    <div class="tab-bar">  <!-- 分类标签 --> </div>
    <div class="template-grid">  <!-- 模版卡片网格 --> </div>
    <textarea id="card-subject" placeholder="输入主体描述...">
    <button id="card-draw-btn">开始抽卡</button>
  </div>
  <!-- ② 抽卡步骤展示区 (初始隐藏) -->
  <div id="card-steps" class="hidden">
    <div class="step-card" data-step="1">  <!-- 扩写步骤 --> </div>
    <div class="step-card" data-step="2">  <!-- 参数配置 --> </div>
    <div class="step-card" data-step="3">  <!-- 生成进度 --> </div>
    <div class="step-card" data-step="4">  <!-- 结果展示 --> </div>
  </div>
</div>
```

### 4.2 状态管理

前端维护以下状态：

```javascript
const state = {
  step: 0,                    // 0=选模版, 1=扩写中, 2=扩写完成, 3=生成中, 4=结果
  selectedTemplate: null,      // 当前选中模版
  subject: "",                 // 主体描述
  expandedPrompt: "",          // 扩写后的完整 prompt
  result: null,                // 生成结果 {url, original_url}
  error: null,                 // 错误信息
};
```

### 4.3 步骤动画

| 步骤 | 动画效果 | 持续时间 |
|------|---------|---------|
| Step 1 → 扩写开始 | 卡片滑入，显示"扩写中..." | API 调用时间 |
| Step 1 → 扩写完成 | 打字机效果逐字显示扩写文字 | 300ms + 文字量 |
| Step 2 → 参数配置 | 卡片淡入，显示推荐参数 | 800ms |
| Step 3 → 生成进度 | 进度条从 0→100% 模拟 | 2.5s |
| Step 4 → 结果 | 图片淡入 + 操作按钮总淡入 | 500ms |

### 4.4 交互细节

- 点击分类标签 → 过滤下方模版卡片
- 点击模版卡片 → 高亮，subject 输入框 placeholder 切换为模版示例
- 编辑 subject 后 → 按钮启用（默认灰色禁用）
- 点击"开始抽卡" → 按钮禁用，步骤区渐入
- 抽卡过程中点击其他模版 → 重置状态
- "重新抽卡" → 不清除模版选择，重新从 Step 1 开始

---

## 5. 错误处理

| 场景 | 前端表现 | 后端处理 |
|------|---------|---------|
| 无 SENSENOVA_API_KEY | Step 1 直接跳过到 Step 2 | `_expand_prompt` 返回原 prompt |
| 扩写失败 | Step 1 显示"跳过扩写，使用原 prompt" | 捕获异常，返回 `{expanded: original}` |
| 生成失败 | Step 4 显示错误卡片 + 错误原因 + 重试按钮 | 返回 `{error, step, expanded?}` |
| 配额用尽 | 检测到 429，显示"配额可能已用尽" | 返回可读错误消息 |

---

## 6. 测试

| 测试 | 类型 | 说明 |
|------|------|------|
| `/api/templates` 返回 200 | 冒烟 | 验证路由正常 |
| `/api/templates` 模版数量 | 冒烟 | 至少返回 8 个模版 |
| `/api/optimize` 参数验证 | 冒烟 | 缺少 subject 时返回 400 |

---

## 7. 文件改动清单

| 文件 | 改动 | 估算行数 |
|------|------|---------|
| `web.py` | + 模版常量列表 (80行) + `/api/templates` (10行) + `/api/optimize` (50行) | ~140 |
| `templates/index.html` | + 抽卡卡片 HTML (~50行) + CSS (~40行) + JS 状态机 (~120行) | ~210 |
| `tests/test_web.py` | + 2 个测试函数 | ~30 |

**不改动**: `src/*`、`main.py`、`.gitignore`
