# 智能抽卡优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 auto_motion Web 控制台中新增「智能抽卡」面板，提供预制模版 + 逐步骤可视化 prompt 优化体验。

**Architecture:** 后端在 `web.py` 中新增模版常量和两个 API 路由，前端在 `templates/index.html` 中插入新卡片区域并实现 JS 状态机 + 步骤动画。复用已有的 `_expand_prompt` 和 `_sensenova_generate_image`。

**Tech Stack:** Flask (Python), vanilla JS + CSS, SenseNova API (sensenova-6.7-flash-lite + sensenova-u1-fast)

---

### Task 1: 后端 — 模版数据 + `/api/templates` 路由

**Files:**
- Modify: `web.py` (新增模版数据 + GET 路由)
- Test: `tests/test_web.py`

- [ ] **Step 1: 在 web.py 顶部添加 PromptTemplate 和模版列表**

在 `SENSENOVA_DEFAULT_SIZE` 之后、`_download_and_save` 之前添加：

```python
from dataclasses import dataclass, asdict


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
]
```

- [ ] **Step 2: 添加 `/api/templates` 路由**

在 `serve_output` 路由之前（或其他合适位置）添加：

```python
@app.route("/api/templates")
def api_templates():
    return jsonify({
        "templates": [asdict(t) for t in CARD_TEMPLATES]
    })
```

- [ ] **Step 3: 写测试**

在 `tests/test_web.py` 末尾添加：

```python
def test_templates_route() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/api/templates")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "templates" in data
        assert len(data["templates"]) >= 8


def test_templates_structure() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/api/templates")
        data = resp.get_json()
        t = data["templates"][0]
        assert set(t.keys()) == {"id", "category", "icon", "name", "desc", "template", "params"}
        assert "params" in t
        assert "model" in t["params"]
        assert "size" in t["params"]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_web.py::test_templates_route tests/test_web.py::test_templates_structure -v
```
Expected: 2 PASS

- [ ] **Step 5: 提交**

```bash
git add web.py tests/test_web.py
git commit -m "feat: add prompt template data and /api/templates endpoint

添加 8 个预制提示词模版（人像、风光、赛博朋克、信息图、水彩、复古）
和 GET /api/templates 路由，返回完整模版列表"
```

---

### Task 2: 后端 — `/api/optimize` 路由

**Files:**
- Modify: `web.py` (新增 POST 路由)
- Test: `tests/test_web.py`

- [ ] **Step 1: 写失败测试**

```python
def test_optimize_missing_subject() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


def test_optimize_without_api_key() -> None:
    """无 SENSENOVA_API_KEY 时不应崩溃，应返回错误信息"""
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={
            "template_id": "portrait_01",
            "subject": "test",
        })
        assert resp.status_code in (200, 400, 502)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest tests/test_web.py::test_optimize_missing_subject tests/test_web.py::test_optimize_without_api_key -v
```

- [ ] **Step 3: 实现 `/api/optimize` 路由**

在 `/api/templates` 路由之后添加：

```python
@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    data = request.get_json()
    if not data or not data.get("subject"):
        return jsonify({"error": "缺少 subject"}), 400

    settings = Settings.from_env()
    subject = data["subject"]
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

    # Step 1: 扩写
    expanded = final_prompt
    try:
        expanded = asyncio.run(_expand_prompt(settings, final_prompt))
    except Exception:
        pass  # 扩写失败则使用原 prompt

    # Step 2+3: 生成图像
    try:
        size = params.get("size", "2048x2048")
        image_url = asyncio.run(
            _sensenova_generate_image(settings, expanded, size)
        )
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_web.py::test_optimize_missing_subject -v
```
Expected: PASS

```bash
uv run pytest tests/test_web.py::test_optimize_without_api_key -v
```
Expected: PASS (返回 502 或 400，不崩溃)

- [ ] **Step 5: 全量测试**

```bash
uv run pytest tests/ -v
```
Expected: 8 PASS (原有 6 + 新增 2)

- [ ] **Step 6: 提交**

```bash
git add web.py tests/test_web.py
git commit -m "feat: add /api/optimize endpoint with step-by-step pipeline

POST /api/optimize 接收 template_id + subject，依次执行扩写和图像生成，
返回原始 prompt、扩写结果、参数配置、图像 URL。扩写失败不阻断流程。"
```

---

### Task 3: 前端 — 抽卡 HTML + CSS

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: 在图像卡片和视频卡片之间插入抽卡 HTML**

在 `</div>` (图像卡片结束) 和 `<div class="card">` (视频卡片开始) 之间插入：

```html
  <!-- 🎴 智能抽卡 -->
  <div class="card" id="card-section">
    <h2>🎴 智能抽卡</h2>

    <!-- ① 模版选择区 -->
    <div id="card-templates">
      <div class="tab-bar" id="card-tabs"></div>
      <div class="template-grid" id="card-grid"></div>
      <div class="form-group">
        <textarea id="card-subject" placeholder="选一个模版，然后在这里输入主体描述（如 'a young woman with freckles'）..." rows="2"></textarea>
      </div>
      <div class="btn-group" style="justify-content:space-between">
        <span id="card-tip" style="font-size:12px;color:#8e8e93;align-self:center"></span>
        <button class="btn" id="card-draw-btn" disabled>🎴 开始抽卡</button>
      </div>
    </div>

    <!-- ② 抽卡步骤区 (初始隐藏) -->
    <div id="card-steps" class="card-steps hidden">
      <!-- Step 1: 扩写 -->
      <div class="step-card" data-step="1">
        <div class="step-header"><span class="step-num">1</span> 扩写提示词</div>
        <div class="step-body">
          <div class="step-original"></div>
          <div class="step-divider">↓</div>
          <div class="step-expanded" id="step-expanded-text"></div>
        </div>
      </div>
      <!-- Step 2: 参数配置 -->
      <div class="step-card" data-step="2">
        <div class="step-header"><span class="step-num">2</span> 参数配置</div>
        <div class="step-body">
          <div class="params-grid" id="step-params"></div>
        </div>
      </div>
      <!-- Step 3: 生成进度 -->
      <div class="step-card" data-step="3">
        <div class="step-header"><span class="step-num">3</span> 生成图像</div>
        <div class="step-body">
          <div class="progress-bar"><div class="progress-bar-fill" id="card-progress" style="width:0%"></div></div>
        </div>
      </div>
      <!-- Step 4: 结果 -->
      <div class="step-card" data-step="4">
        <div class="step-header"><span class="step-num">4</span> 抽卡结果</div>
        <div class="step-body" id="step-result-body"></div>
      </div>
    </div>
  </div>
```

- [ ] **Step 2: 添加 CSS 样式**

将以下 CSS 追加到 `<style>` 块末尾（在 `.progress-bar-fill` 规则之后）：

```css
/* 🎴 智能抽卡 */
.tab-bar { display:flex; gap:6px; margin-bottom:12px; flex-wrap:wrap; }
.tab-bar .tab { padding:6px 14px; border-radius:16px; border:1px solid #d2d2d7; background:#fff; font-size:13px; cursor:pointer; transition:all 0.2s; }
.tab-bar .tab:hover { border-color:#0071e3; color:#0071e3; }
.tab-bar .tab.active { background:#0071e3; color:#fff; border-color:#0071e3; }

.template-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:10px; margin-bottom:12px; }
.template-card { border:2px solid #e8e8ed; border-radius:10px; padding:12px; cursor:pointer; transition:all 0.2s; }
.template-card:hover { border-color:#0071e3; transform:translateY(-2px); box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.template-card.selected { border-color:#0071e3; background:#f0f7ff; }
.template-card .t-icon { font-size:24px; margin-bottom:4px; }
.template-card .t-name { font-size:13px; font-weight:600; margin-bottom:2px; }
.template-card .t-desc { font-size:11px; color:#8e8e93; }
.template-card .t-size { font-size:10px; color:#aeaeb2; margin-top:4px; }

.card-steps { margin-top:16px; }
.step-card { background:#f5f5f7; border-radius:10px; padding:14px; margin-bottom:10px; opacity:0; transform:translateY(10px); transition:all 0.4s ease; }
.step-card.visible { opacity:1; transform:translateY(0); }
.step-header { font-size:13px; font-weight:600; margin-bottom:8px; display:flex; align-items:center; gap:6px; }
.step-num { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:50%; background:#0071e3; color:#fff; font-size:12px; font-weight:600; }
.step-body { font-size:13px; color:#1d1d1f; line-height:1.5; }
.step-original { padding:8px; background:#fff; border-radius:6px; border:1px solid #e8e8ed; margin-bottom:4px; font-size:12px; color:#8e8e93; white-space:pre-wrap; }
.step-divider { text-align:center; color:#0071e3; font-size:16px; margin:2px 0; }
.step-expanded { padding:8px; background:#fff; border-radius:6px; border:1px solid #0071e3; font-size:12px; min-height:24px; white-space:pre-wrap; border-left:3px solid #0071e3; }
.step-expanded .cursor { display:inline-block; width:2px; height:14px; background:#0071e3; animation:blink 0.6s step-end infinite; vertical-align:text-bottom; }
@keyframes blink { 50% { opacity:0; } }
.params-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.params-grid .param-item { padding:8px; background:#fff; border-radius:6px; display:flex; flex-direction:column; }
.params-grid .param-label { font-size:11px; color:#8e8e93; }
.params-grid .param-value { font-size:14px; font-weight:500; }

#step-result-body { text-align:center; }
#step-result-body img { max-width:100%; max-height:350px; border-radius:8px; margin-bottom:8px; }
.result-actions { display:flex; gap:8px; justify-content:center; margin-top:8px; flex-wrap:wrap; }
.result-actions .btn-sm { padding:6px 14px; background:#e8e8ed; color:#1d1d1f; border:none; border-radius:6px; font-size:12px; cursor:pointer; text-decoration:none; }
.result-actions .btn-sm:hover { background:#d2d2d7; }
```

- [ ] **Step 3: 提交**

```bash
git add templates/index.html
git commit -m "feat: add card-drawing HTML and CSS layout

在图像/视频生成卡片之间插入智能抽卡面板，
包含模版选择区、分类标签、步骤展示区（4步动画卡片）"
```

---

### Task 4: 前端 — JS 状态机与动画

**Files:**
- Modify: `templates/index.html` (在底部 `<script>` 块末尾追加)

- [ ] **Step 1: 在现有 `<script>` 末尾追加抽卡 JS**

在最后一个 `</script>` 之前追加：

```javascript
// 🎴 智能抽卡 — 状态机
(function() {
  const state = { step: 0, selectedTemplate: null, subject: "", expandedPrompt: "", result: null, error: null };
  let categories = [];
  let allTemplates = [];
  let typewriterTimer = null;

  // 加载模版
  async function loadTemplates() {
    try {
      const resp = await fetch("/api/templates");
      const data = await resp.json();
      allTemplates = data.templates;
      // 提取分类
      const cats = new Set(allTemplates.map(t => t.category));
      categories = Array.from(cats);
      renderTabs();
      renderGrid(categories[0]);
    } catch (e) {
      document.getElementById("card-tabs").innerHTML = "<span style='color:#ff3b30'>加载模版失败</span>";
    }
  }

  function renderTabs(activeCat) {
    const tabBar = document.getElementById("card-tabs");
    const firstCat = activeCat || categories[0];
    tabBar.innerHTML = categories.map(c =>
      `<span class="tab ${c === firstCat ? 'active' : ''}" data-cat="${c}">${c}</span>`
    ).join("");
    tabBar.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        tabBar.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        renderGrid(tab.dataset.cat);
      });
    });
  }

  function renderGrid(category) {
    const grid = document.getElementById("card-grid");
    const filtered = allTemplates.filter(t => t.category === category);
    grid.innerHTML = filtered.map(t =>
      `<div class="template-card" data-id="${t.id}">
        <div class="t-icon">${t.icon}</div>
        <div class="t-name">${t.name}</div>
        <div class="t-desc">${t.desc}</div>
        <div class="t-size">建议: ${t.params.size}</div>
      </div>`
    ).join("");
    grid.querySelectorAll(".template-card").forEach(card => {
      card.addEventListener("click", () => {
        grid.querySelectorAll(".template-card").forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        const tpl = allTemplates.find(t => t.id === card.dataset.id);
        state.selectedTemplate = tpl;
        document.getElementById("card-subject").placeholder = `模版已选「${tpl.name}」，输入主体描述...`;
        document.getElementById("card-tip").textContent = `已选: ${tpl.icon} ${tpl.name}`;
        checkCanDraw();
      });
    });
  }

  function checkCanDraw() {
    const btn = document.getElementById("card-draw-btn");
    const subj = document.getElementById("card-subject").value.trim();
    btn.disabled = !(state.selectedTemplate && subj.length > 0);
  }

  // 开始抽卡
  async function startDraw() {
    const subject = document.getElementById("card-subject").value.trim();
    if (!subject || !state.selectedTemplate) return;

    // 重置步骤
    resetSteps();
    state.error = null;
    state.result = null;
    document.getElementById("card-draw-btn").disabled = true;
    document.getElementById("card-templates").classList.add("hidden");
    document.getElementById("card-steps").classList.remove("hidden");

    // Step 1: 扩写中
    showStep(1);
    document.querySelector("#card-steps .step-card[data-step='1'] .step-original").textContent = subject;

    const resp = await fetch("/api/optimize", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        template_id: state.selectedTemplate.id,
        subject: subject,
      }),
    });
    const data = await resp.json();

    // Step 1: 显示扩写结果（打字机效果）
    if (data.expanded) {
      typewriterEffect("step-expanded-text", data.expanded, () => {
        // Step 2: 参数配置
        setTimeout(() => showStep(2), 300);
        renderParams(data.params || {});
      });
    }

    // 追加 Step 2 回调
    const showStep3 = () => {
      setTimeout(() => {
        showStep(3);
        animateProgress(() => {
          showStep(4);
          renderResult(data, resp.ok);
          document.getElementById("card-draw-btn").disabled = false;
        });
      }, 500);
    };

    // 监听打字机完成事件
    const checkDone = setInterval(() => {
      if (document.getElementById("step-expanded-text").dataset.done === "true") {
        clearInterval(checkDone);
        setTimeout(() => showStep(2), 300);
        renderParams(data.params || {});
        setTimeout(showStep3, 800);
      }
    }, 200);
  }

  function showStep(n) {
    document.querySelectorAll(".step-card").forEach(c => c.classList.remove("visible"));
    document.querySelectorAll(`.step-card[data-step]`).forEach(c => {
      if (parseInt(c.dataset.step) <= n) c.classList.add("visible");
    });
  }

  function typewriterEffect(elId, text, cb) {
    const el = document.getElementById(elId);
    el.textContent = "";
    el.dataset.done = "false";
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        el.textContent = text.slice(0, i + 1);
        el.innerHTML = text.slice(0, i + 1) + '<span class="cursor"></span>';
        i++;
      } else {
        clearInterval(timer);
        el.innerHTML = text;
        el.dataset.done = "true";
        if (cb) cb();
      }
    }, 20);
  }

  function renderParams(params) {
    const grid = document.getElementById("step-params");
    grid.innerHTML = Object.entries(params).map(([k, v]) =>
      `<div class="param-item"><span class="param-label">${k}</span><span class="param-value">${v}</span></div>`
    ).join("");
  }

  function animateProgress(cb) {
    const bar = document.getElementById("card-progress");
    let pct = 0;
    const timer = setInterval(() => {
      pct += Math.random() * 8 + 2;
      if (pct >= 100) { pct = 100; clearInterval(timer); if (cb) cb(); }
      bar.style.width = `${Math.min(pct, 100)}%`;
    }, 150);
  }

  function renderResult(data, ok) {
    const body = document.getElementById("step-result-body");
    if (!ok || data.error) {
      body.innerHTML = `
        <div class="error-msg">❌ ${data.error || "生成失败"}</div>
        <div class="result-actions">
          <button class="btn-sm" onclick="document.getElementById('card-draw-btn').click()">重试</button>
        </div>`;
      return;
    }
    body.innerHTML = `
      <img src="${data.url}" alt="生成结果" onerror="this.after('<div class=error-msg>图片加载失败</div>');this.remove()">
      <div class="result-actions">
        <a class="btn-sm" href="${data.url}" download>⬇ 下载</a>
        <button class="btn-sm" id="copy-prompt-btn">📋 复制 Prompt</button>
        <button class="btn-sm" id="redraw-btn">🔄 重新抽卡</button>
      </div>`;
    document.getElementById("copy-prompt-btn")?.addEventListener("click", () => {
      navigator.clipboard.writeText(data.expanded || "").then(() => {
        const btn = document.getElementById("copy-prompt-btn");
        btn.textContent = "✅ 已复制";
        setTimeout(() => { btn.textContent = "📋 复制 Prompt"; }, 2000);
      });
    });
    document.getElementById("redraw-btn")?.addEventListener("click", resetAndDraw);
  }

  function resetSteps() {
    document.getElementById("card-progress").style.width = "0%";
    document.getElementById("step-expanded-text").textContent = "";
    document.getElementById("step-expanded-text").dataset.done = "false";
    document.getElementById("step-params").innerHTML = "";
    document.getElementById("step-result-body").innerHTML = "";
  }

  function resetAndDraw() {
    document.getElementById("card-steps").classList.add("hidden");
    document.getElementById("card-templates").classList.remove("hidden");
    resetSteps();
    if (typewriterTimer) clearInterval(typewriterTimer);
    startDraw();
  }

  // 事件绑定
  document.addEventListener("DOMContentLoaded", () => {
    loadTemplates();
    document.getElementById("card-subject").addEventListener("input", checkCanDraw);
    document.getElementById("card-draw-btn").addEventListener("click", startDraw);
  });
})();
```

- [ ] **Step 2: 运行前端测试**

```bash
uv run pytest tests/test_web.py -v
```
Expected: 8 PASS (前端改动不影响后端)

- [ ] **Step 3: 提交**

```bash
git add templates/index.html
git commit -m "feat: implement card-drawing JS state machine and animations

实现智能抽卡前端逻辑：模版加载与选择、分类过滤、
打字机效果展示扩写结果、参数卡片展示、进度条动画、结果展示与操作"
```

---

### Task 5: 最终验证

- [ ] **Step 1: 运行全量测试**

```bash
uv run pytest tests/ -v
```
Expected: 8 PASS

- [ ] **Step 2: 推送分支**

```bash
git push origin feat/prompt-card-drawing
```

- [ ] **Step 3: 确认 git log 干净**

```bash
git status
```
Expected: 无未提交文件
