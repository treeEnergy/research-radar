# Keyword / Topic Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "管理话题" slide panel to `index.html` that lets users add/delete research topics with AI-generated search terms, immediately matching existing papers via local keyword matching.

**Architecture:** All new code goes into the single `index.html` file (existing pattern — no build tools, no separate JS files). Topics are persisted in `localStorage` under `ls_topics`; user-applied topic overrides (labels added to specific papers) are stored separately under `ls_topic_overrides`. The pipeline reads `data/topics.json` if present (committed via GitHub API) as a bonus feature.

**Tech Stack:** Vanilla JS, HTML/CSS inline in `index.html`; DeepSeek API (same key already used for chat); localStorage (same pattern as annotations); GitHub Contents API (same pattern as pipeline trigger).

---

## File Structure

- **Modify:** `index.html` — all tasks touch this file only (except Task 10 which also touches `scripts/run_pipeline.py`)
- **Create:** `data/topics.json` — created by the "同步到流水线" button at runtime, not by this plan

---

## Task 1: localStorage constants + topic storage helpers

**File:** `index.html` — JS section starting at line ~2138

**Context:** The file currently has four `LS_*` constants and `getAnnotations/saveAnnotations/getCustomGroups/saveCustomGroups` helpers. We add `LS_TOPICS` and `LS_TOPIC_OVERRIDES` plus their accessors, and a `DEFAULT_TOPICS` constant seeded from the current config.py keywords.

- [ ] **Step 1: Add the two new LS constants** right after the existing four `LS_*` lines (after `const LS_GITHUB_TOKEN = 'rr_github_token';`)

```javascript
const LS_TOPICS          = 'rr_topics';
const LS_TOPIC_OVERRIDES = 'rr_topic_overrides';
```

- [ ] **Step 2: Add `DEFAULT_TOPICS`** — a hardcoded array mirroring the current `config.py` keywords, grouped into five topics. Place it right after the two new constants:

```javascript
const DEFAULT_TOPICS = [
  {
    label: '叶尖间隙',
    terms: ['compressor tip clearance', 'non-axisymmetric tip clearance', 'tip clearance effect'],
    builtin: true
  },
  {
    label: '机匣处理',
    terms: ['casing treatment stall margin', 'casing treatment'],
    builtin: true
  },
  {
    label: '压缩机稳定性',
    terms: ['axial compressor rotating stall', 'compressor stability', 'compressor surge', 'stall inception compressor'],
    builtin: true
  },
  {
    label: '稳定性建模',
    terms: ['actuator disk model compressor', 'actuator disk model fan', 'compressor stability model',
            'three-dimensional stability model turbomachinery', 'Moore Greitzer model compressor',
            'body force model compressor'],
    builtin: true
  },
  {
    label: '进气畸变',
    terms: ['inlet distortion compressor', 'circumferential distortion compressor',
            'inlet distortion fan', 'total pressure distortion turbomachinery'],
    builtin: true
  }
];
```

- [ ] **Step 3: Add topic accessor helpers** right after `saveCustomGroups`:

```javascript
function getTopics() {
  const stored = lsGet(LS_TOPICS, null);
  if (stored === null) {
    lsSet(LS_TOPICS, DEFAULT_TOPICS);
    return DEFAULT_TOPICS;
  }
  return stored;
}
function saveTopics(data)          { lsSet(LS_TOPICS, data); }
function getTopicOverrides()       { return lsGet(LS_TOPIC_OVERRIDES, {}); }
function saveTopicOverrides(data)  { lsSet(LS_TOPIC_OVERRIDES, data); }
```

- [ ] **Step 4: Verify in browser console**

Open `index.html` in browser (or refresh). Open DevTools console, run:
```javascript
getTopics()
```
Expected: array of 5 objects with `{label, terms, builtin: true}`.

Run again after refreshing — should return same array from `localStorage` (not recreate).

- [ ] **Step 5: Commit**

```bash
cd "E:/claude-project/20260327"
git add index.html
git commit -m "feat(topics): add localStorage constants and topic storage helpers"
```

---

## Task 2: `matchesTopic()` and `effectiveTags()` helpers

**File:** `index.html` — JS section, after the topic accessor helpers from Task 1

**Context:** `matchesTopic` does case-insensitive substring search across paper fields. `effectiveTags` merges AI-assigned tags (`paper.tags`) with user-added overrides from `ls_topic_overrides`. These functions are used in Tasks 3, 7, 8, and 9.

- [ ] **Step 1: Add `matchesTopic` and `effectiveTags`** directly after `saveTopicOverrides`:

```javascript
/**
 * Returns true if any term in `terms` appears (case-insensitive) in the paper's
 * title, abstract, or keywords fields.
 */
function matchesTopic(paper, terms) {
  const haystack = [
    paper.title || '',
    paper.abstract || '',
    (paper.keywords || []).join(' ')
  ].join(' ').toLowerCase();
  return terms.some(t => haystack.includes(t.toLowerCase()));
}

/**
 * Returns the effective tag set for a paper: AI-assigned tags merged with
 * any user-added topic overrides, deduplicated.
 */
function effectiveTags(paper) {
  const overrides = getTopicOverrides();
  const extra = overrides[paper.id] || [];
  const base  = paper.tags || [];
  return [...new Set([...base, ...extra])];
}
```

- [ ] **Step 2: Verify `matchesTopic` in browser console**

```javascript
// papers is already loaded; pick the first paper and test
matchesTopic(papers[0], ['compressor'])
// Expected: true or false depending on paper content — just verify no error
matchesTopic(papers[0], ['zzznomatch999xyz'])
// Expected: false
```

- [ ] **Step 3: Verify `effectiveTags` in browser console**

```javascript
effectiveTags(papers[0])
// Expected: same as papers[0].tags (no overrides yet)
```

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(topics): add matchesTopic and effectiveTags helpers"
```

---

## Task 3: Update `render()` and `buildTags()` to use `effectiveTags()`

**File:** `index.html` — `buildTags()` at line ~2239, `render()` at line ~2258

**Context:** Currently these functions use `p.tags||[]` directly. We replace them with `effectiveTags(p)` so user-added topic overrides appear in the tag filter bar and paper cards. Also update the tag display in the paper card HTML template.

- [ ] **Step 1: Update `buildTags()`**

Find this line (line ~2241):
```javascript
  papers.forEach(p => (p.tags||[]).forEach(t => tags.add(t)));
```
Replace with:
```javascript
  papers.forEach(p => effectiveTags(p).forEach(t => tags.add(t)));
```

- [ ] **Step 2: Update the `activeTag` filter in `render()`**

Find this line (line ~2265):
```javascript
    if (activeTag   && !(p.tags||[]).includes(activeTag))    return false;
```
Replace with:
```javascript
    if (activeTag   && !effectiveTags(p).includes(activeTag))    return false;
```

- [ ] **Step 3: Update the tags display in the paper card template**

Find this line (line ~2313):
```javascript
    const tags = (p.tags||[]).map(t => `<span class="ptag">${t}</span>`).join('');
```
Replace with:
```javascript
    const tags = effectiveTags(p).map(t => `<span class="ptag">${t}</span>`).join('');
```

- [ ] **Step 4: Also update `sendChat()` which uses `p.tags`**

Find this line (line ~2983):
```javascript
      (p.tags || []).join(' '),
```
Replace with:
```javascript
      effectiveTags(p).join(' '),
```

Find this line (line ~3042):
```javascript
        if (p.tags?.length) parts.push(`  标签: ${p.tags.join(', ')}`)
```
Replace with:
```javascript
        if (effectiveTags(p).length) parts.push(`  标签: ${effectiveTags(p).join(', ')}`)
```

- [ ] **Step 5: Verify in browser**

Open browser, load page. Tag filter bar should show same tags as before (no regressions). Paper cards should show same tags. No console errors.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat(topics): use effectiveTags() in render, buildTags, sendChat"
```

---

## Task 4: Topics panel HTML

**File:** `index.html` — HTML section, after the `pipeline-panel` div (line ~1331+)

**Context:** The pipeline panel (`id="pipeline-panel"`) is a right-side slide drawer starting at line 1332. We add a similar drawer for topic management. It contains: header, scrollable topic card list, and an "add topic" section at the bottom.

- [ ] **Step 1: Add the topics panel HTML** immediately after the closing `</div>` of the `pipeline-panel` div (find `<!-- 流水线进度面板（右侧抽屉） -->` comment, then find the matching closing `</div>` for the panel, then insert after it):

```html
<!-- 话题管理面板（右侧抽屉） -->
<div id="topics-panel" style="
  position:fixed; top:56px; right:0; bottom:0; width:380px;
  background:var(--bg2); border-left:1px solid var(--border2);
  display:flex; flex-direction:column;
  transform:translateX(100%); transition:transform .25s ease;
  z-index:501;
">
  <!-- 标题栏 -->
  <div style="padding:14px 18px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:10px; flex-shrink:0;">
    <span style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--gold); letter-spacing:.08em; flex:1;">话题管理</span>
    <button onclick="closeTopicsPanel()" style="background:none; border:none; color:var(--text3); font-size:18px; cursor:pointer; line-height:1; padding:0 2px;">×</button>
  </div>
  <div style="padding:4px 18px 8px; flex-shrink:0;">
    <div style="color:var(--text3); font-size:11px;">管理研究关键词，自动更新论文分类</div>
  </div>

  <!-- 话题卡片列表（可滚动） -->
  <div id="topics-list" style="flex:1; overflow-y:auto; padding:0 18px 8px;">
    <!-- 由 renderTopicsPanel() 填充 -->
  </div>

  <!-- 添加新话题区域 -->
  <div id="topics-add-area" style="padding:14px 18px; border-top:1px solid var(--border); flex-shrink:0;">
    <div style="color:var(--text3); font-size:10px; letter-spacing:.08em; margin-bottom:8px;">添加新话题</div>
    <input id="topic-input" type="text"
      placeholder="输入话题，如：转子叶尖泄漏"
      style="width:100%; background:var(--bg); border:1px solid var(--border2); border-radius:4px;
             padding:8px 10px; color:var(--text); font-family:'IBM Plex Mono',monospace; font-size:12px; outline:none;"
      onkeydown="if(event.key==='Enter') generateTopic()" />
    <button id="topic-generate-btn" onclick="generateTopic()" style="
      width:100%; margin-top:8px; background:var(--gold); border:none; color:#111;
      padding:8px; border-radius:4px; font-size:12px; font-weight:600; cursor:pointer;
      font-family:'IBM Plex Mono',monospace; letter-spacing:.04em;
    ">✦ AI 生成并添加</button>
    <div id="topic-generate-error" style="display:none; margin-top:8px; color:var(--rel5); font-size:11px; font-family:'IBM Plex Mono',monospace;"></div>
  </div>

  <!-- 同步到流水线按钮 -->
  <div style="padding:10px 18px 14px; border-top:1px solid var(--border); flex-shrink:0;">
    <button onclick="syncTopicsToPipeline()" style="
      width:100%; background:transparent; border:1px solid var(--border2);
      color:var(--text3); padding:7px; border-radius:4px; font-size:11px; cursor:pointer;
      font-family:'IBM Plex Mono',monospace;
    ">↑ 同步到流水线 (data/topics.json)</button>
  </div>
</div>

<!-- 话题删除确认弹窗 -->
<div id="topic-delete-overlay" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:600; align-items:center; justify-content:center;">
  <div style="background:var(--bg2); border:1px solid var(--border2); border-radius:8px; padding:24px 28px; width:320px; font-family:'IBM Plex Mono',monospace;">
    <div style="color:var(--text); font-size:13px; margin-bottom:8px;">删除话题</div>
    <div id="topic-delete-msg" style="color:var(--text3); font-size:12px; margin-bottom:20px;"></div>
    <div style="display:flex; gap:10px;">
      <button onclick="closeTopicDeleteOverlay()" style="flex:1; background:transparent; border:1px solid var(--border2); color:var(--text3); padding:8px; border-radius:4px; font-size:12px; cursor:pointer;">取消</button>
      <button id="topic-delete-confirm-btn" style="flex:1; background:var(--rel5); border:none; color:#fff; padding:8px; border-radius:4px; font-size:12px; font-weight:600; cursor:pointer;">删除</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verify HTML renders**

Open browser, open DevTools Elements tab, verify `id="topics-panel"` and `id="topic-delete-overlay"` elements are present in the DOM. Panel should be off-screen (translateX(100%)).

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(topics): add topics panel and delete overlay HTML"
```

---

## Task 5: Topics panel CSS

**File:** `index.html` — CSS section (inside `<style>` block)

**Context:** Need styles for topic cards (`.topic-card`), search term chips (`.term-chip`), and the topics list. Add these after the existing `.ptag` style (line ~585) or at the end of the `<style>` block.

- [ ] **Step 1: Add topic panel CSS** at the end of the `<style>` block, just before the closing `</style>` tag:

```css
/* ── Topics Panel ── */
.topic-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
}
.topic-card-header {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; cursor: pointer;
  user-select: none;
}
.topic-card-header:hover { background: rgba(255,255,255,.03); }
.topic-card-label {
  flex: 1; color: var(--text); font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
}
.topic-card-count {
  color: var(--blue); font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
}
.topic-card-toggle {
  color: var(--text3); font-size: 12px; transition: transform .2s;
}
.topic-card.expanded .topic-card-toggle { transform: rotate(90deg); }
.topic-card-body { display: none; padding: 0 12px 12px; }
.topic-card.expanded .topic-card-body { display: block; }
.topic-card-terms {
  display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px;
}
.term-chip {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--bg); border: 1px solid var(--border2);
  border-radius: 3px; padding: 2px 8px;
  font-size: 10px; color: var(--text3);
  font-family: 'IBM Plex Mono', monospace;
}
.term-chip-remove {
  color: var(--rel5); cursor: pointer; font-size: 11px;
  line-height: 1; padding: 0 1px;
}
.term-chip-remove:hover { color: #ff6060; }
.topic-card-actions {
  display: flex; justify-content: flex-end; margin-top: 4px;
}
.topic-delete-btn {
  background: transparent; border: 1px solid var(--rel5);
  color: var(--rel5); padding: 3px 10px; border-radius: 3px;
  font-size: 10px; cursor: pointer;
  font-family: 'IBM Plex Mono', monospace;
}
.topic-delete-btn:hover { background: var(--rel5-bg); }
.topic-builtin-badge {
  color: var(--text3); font-size: 10px;
  font-family: 'IBM Plex Mono', monospace; opacity: .6;
}
/* preview card shown in the "add" area */
.topic-preview-card {
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 6px; padding: 12px;
}
.topic-preview-label-input {
  width: 100%; background: var(--bg); border: 1px solid var(--border2);
  border-radius: 4px; padding: 6px 10px; color: var(--text);
  font-family: 'IBM Plex Mono', monospace; font-size: 12px; outline: none;
  margin-bottom: 10px;
}
.topic-preview-terms {
  display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px;
}
.term-chip-preview {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--bg); border: 1px solid var(--blue);
  border-radius: 3px; padding: 2px 8px;
  font-size: 10px; color: var(--blue);
  font-family: 'IBM Plex Mono', monospace;
}
.term-chip-add {
  background: transparent; border: 1px dashed var(--border2);
  border-radius: 3px; padding: 2px 8px;
  font-size: 10px; color: var(--text3); cursor: pointer;
  font-family: 'IBM Plex Mono', monospace;
}
.topic-preview-hit {
  color: var(--text3); font-size: 11px; margin-bottom: 10px;
  font-family: 'IBM Plex Mono', monospace;
}
.topic-preview-hit span { color: var(--rel3); }
.topic-preview-actions { display: flex; gap: 8px; }
```

- [ ] **Step 2: Verify styles load**

Open browser, open DevTools, check Elements → verify `.topic-card` styles are present in the stylesheet. No CSS parse errors in console.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(topics): add topic panel CSS"
```

---

## Task 6: "管理话题" button in header

**File:** `index.html` — header section, line ~1317 (`div.header-meta`)

**Context:** The header-meta div currently contains a status dot, a meta text span, and the `▶ 更新检索` button. We add a "管理话题" button to the left of the run button.

- [ ] **Step 1: Find the run button and add the manage-topics button before it**

Find this block (line ~1320):
```html
    <button id="run-btn" onclick="runPipeline()" style="
      margin-left:20px; padding:0 14px; height:30px;
```

Insert the following immediately before that button (keep the blank line):
```html
    <button id="topics-btn" onclick="openTopicsPanel()" style="
      margin-left:20px; padding:0 14px; height:30px;
      font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.06em;
      background:none; border:1px solid var(--border2); border-radius:3px;
      color:var(--text3); cursor:pointer; transition:all .2s;
    " onmouseover="this.style.borderColor='var(--blue)';this.style.color='var(--blue)'"
       onmouseout="this.style.borderColor='var(--border2)';this.style.color='var(--text3)'">
      🏷 管理话题
    </button>
```

- [ ] **Step 2: Verify button appears**

Open browser, verify "🏷 管理话题" button appears in the header to the left of "▶ 更新检索". Clicking it should not throw errors (function `openTopicsPanel` not yet defined — console error is expected, panel won't open yet).

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(topics): add 管理话题 button to header"
```

---

## Task 7: `renderTopicsPanel()`, `openTopicsPanel()`, `closeTopicsPanel()`

**File:** `index.html` — JS section, after the existing `closePipelinePanel` function (line ~2722)

**Context:** `renderTopicsPanel()` populates `#topics-list` with topic cards (C2 card expansion style). Cards show hit count and expand/collapse to show search term chips. Non-builtin cards have a delete button. `openTopicsPanel()` renders and slides the panel in. `closeTopicsPanel()` slides it out.

- [ ] **Step 1: Add the panel open/close functions**

```javascript
function openTopicsPanel() {
  renderTopicsPanel();
  document.getElementById('topics-panel').style.transform = 'translateX(0)';
}

function closeTopicsPanel() {
  document.getElementById('topics-panel').style.transform = 'translateX(100%)';
}
```

- [ ] **Step 2: Add `renderTopicsPanel()`**

```javascript
function renderTopicsPanel() {
  const topics = getTopics();
  const listEl = document.getElementById('topics-list');

  const countLabel = `当前话题 · ${topics.length} 个`;
  listEl.innerHTML = `<div style="color:var(--text3);font-size:10px;letter-spacing:.08em;padding:10px 0 8px;">${countLabel}</div>`;

  topics.forEach((topic, idx) => {
    const hitCount = papers.filter(p => matchesTopic(p, topic.terms)).length;

    const card = document.createElement('div');
    card.className = 'topic-card';
    card.id = `topic-card-${idx}`;

    const headerHtml = `
      <div class="topic-card-header" onclick="toggleTopicCard(${idx})">
        <span class="topic-card-label">${topic.label}</span>
        ${topic.builtin ? '<span class="topic-builtin-badge">🔒</span>' : ''}
        <span class="topic-card-count">${hitCount} 篇</span>
        <span class="topic-card-toggle">›</span>
      </div>`;

    const termChips = topic.terms.map(t =>
      `<span class="term-chip">${t}</span>`
    ).join('');

    const deleteBtn = topic.builtin
      ? ''
      : `<div class="topic-card-actions">
           <button class="topic-delete-btn" onclick="confirmDeleteTopic(${idx})">删除话题</button>
         </div>`;

    card.innerHTML = headerHtml + `
      <div class="topic-card-body">
        <div class="topic-card-terms">${termChips}</div>
        ${deleteBtn}
      </div>`;

    listEl.appendChild(card);
  });
}

function toggleTopicCard(idx) {
  const card = document.getElementById(`topic-card-${idx}`);
  card.classList.toggle('expanded');
}
```

- [ ] **Step 3: Verify panel opens and shows cards**

Open browser, click "🏷 管理话题". Panel should slide in from the right. Should display 5 builtin topic cards each showing a hit count. Clicking a card header should expand it showing search term chips. The lock icon (🔒) should appear on builtin topics. The × button in the panel header should close it.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(topics): add renderTopicsPanel, open/close, toggleTopicCard"
```

---

## Task 8: Add topic — AI generation + preview card

**File:** `index.html` — JS section, after `renderTopicsPanel()`

**Context:** `generateTopic()` is called when user clicks "✦ AI 生成并添加". It calls DeepSeek to generate `{label, terms}`, then shows a preview card in `#topics-add-area` where the user can edit the label, remove/add terms, and see the live hit count. The input and generate button are hidden while the preview is shown.

- [ ] **Step 1: Add `generateTopic()` and `callDeepSeekForTopic()`**

```javascript
async function generateTopic() {
  const input = document.getElementById('topic-input').value.trim();
  if (!input) return;

  const apiKey = await ensureDeepseekKey();
  if (!apiKey) return;

  const btn = document.getElementById('topic-generate-btn');
  const errEl = document.getElementById('topic-generate-error');
  btn.textContent = '⟳ AI 生成中…';
  btn.disabled = true;
  errEl.style.display = 'none';

  let result;
  try {
    result = await callDeepSeekForTopic(input, apiKey);
  } catch (e) {
    btn.textContent = '✦ AI 生成并添加';
    btn.disabled = false;
    errEl.textContent = 'AI 生成失败：' + (e.message || '网络错误') + '  ';
    const retryLink = document.createElement('span');
    retryLink.textContent = '[重试]';
    retryLink.style.cssText = 'cursor:pointer;color:var(--gold);';
    retryLink.onclick = generateTopic;
    errEl.appendChild(retryLink);
    errEl.style.display = 'block';
    return;
  }

  btn.textContent = '✦ AI 生成并添加';
  btn.disabled = false;

  showTopicPreview(result.label, result.terms);
}

async function callDeepSeekForTopic(input, apiKey) {
  const prompt = `你是一个学术文献检索专家。用户输入一个研究话题，请生成：
1. 中文标签名（简短，2-6个汉字）
2. 3-6个英文搜索词（用于学术数据库检索，覆盖该话题的主要变体表达）

话题：${input}

以 JSON 格式返回，不要有其他内容：
{"label": "...", "terms": ["...", "...", "..."]}`;

  const resp = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.3,
      max_tokens: 300
    })
  });

  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem(LS_DEEPSEEK_KEY);
      throw new Error('API Key 无效，请重新设置');
    }
    throw new Error(`HTTP ${resp.status}`);
  }

  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content || '';

  // Extract JSON from response (may have markdown code fences)
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error('JSON 解析失败，原始回复：' + content.slice(0, 100));

  let parsed;
  try {
    parsed = JSON.parse(jsonMatch[0]);
  } catch {
    throw new Error('JSON 解析失败，原始回复：' + content.slice(0, 100));
  }

  if (!parsed.label || !Array.isArray(parsed.terms) || parsed.terms.length === 0) {
    throw new Error('AI 返回格式不正确');
  }

  return parsed;
}
```

- [ ] **Step 2: Add `showTopicPreview(label, terms)`**

```javascript
function showTopicPreview(label, terms) {
  // Hide the normal input UI
  document.getElementById('topic-input').style.display = 'none';
  document.getElementById('topic-generate-btn').style.display = 'none';

  const addArea = document.getElementById('topics-add-area');

  // Remove old preview if any
  const oldPreview = document.getElementById('topic-preview');
  if (oldPreview) oldPreview.remove();

  // Build preview card
  const preview = document.createElement('div');
  preview.id = 'topic-preview';

  // Use a mutable array so chip removals update it
  const currentTerms = [...terms];

  const renderPreview = () => {
    const hitCount = papers.filter(p => matchesTopic(p, currentTerms)).length;
    const termChipsHtml = currentTerms.map((t, i) =>
      `<span class="term-chip-preview">
        ${t}
        <span class="term-chip-remove" data-term-idx="${i}">✕</span>
      </span>`
    ).join('') +
    `<span class="term-chip-add" id="term-chip-add-btn">+ 添加</span>`;

    preview.innerHTML = `
      <div class="topic-preview-card">
        <div style="color:var(--gold);font-size:10px;letter-spacing:.08em;margin-bottom:8px;">AI 生成结果 — 请确认</div>
        <div style="color:var(--text3);font-size:10px;margin-bottom:4px;">标签名（可改）</div>
        <input id="preview-label-input" class="topic-preview-label-input"
               value="${label}" placeholder="中文标签名" />
        <div style="color:var(--text3);font-size:10px;margin-bottom:6px;">英文搜索词（可删减）</div>
        <div class="topic-preview-terms" id="preview-terms">${termChipsHtml}</div>
        <div class="topic-preview-hit">预计命中现有论文：<span>${hitCount} 篇</span></div>
        <div class="topic-preview-actions">
          <button onclick="cancelTopicPreview()" style="flex:1;background:transparent;border:1px solid var(--border2);color:var(--text3);padding:7px;border-radius:4px;font-size:11px;cursor:pointer;font-family:'IBM Plex Mono',monospace;">取消</button>
          <button onclick="confirmAddTopic()" style="flex:2;margin-left:8px;background:var(--gold);border:none;color:#111;padding:7px;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;font-family:'IBM Plex Mono',monospace;">确认并更新论文 (${hitCount}篇)</button>
        </div>
      </div>`;

    // Attach remove listeners
    preview.querySelectorAll('.term-chip-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.dataset.termIdx);
        currentTerms.splice(i, 1);
        renderPreview();
      });
    });

    // Attach add listener
    const addBtn = preview.querySelector('#term-chip-add-btn');
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        const newTerm = prompt('输入新搜索词（英文）：');
        if (newTerm?.trim()) {
          currentTerms.push(newTerm.trim());
          renderPreview();
        }
      });
    }

    // Store current state for confirmAddTopic
    preview._currentTerms = currentTerms;
  };

  renderPreview();
  addArea.appendChild(preview);
}
```

- [ ] **Step 3: Add `cancelTopicPreview()`**

```javascript
function cancelTopicPreview() {
  document.getElementById('topic-preview')?.remove();
  document.getElementById('topic-input').style.display = '';
  document.getElementById('topic-input').value = '';
  document.getElementById('topic-generate-btn').style.display = '';
  document.getElementById('topic-generate-error').style.display = 'none';
}
```

- [ ] **Step 4: Verify AI generation and preview**

1. Open browser, click "🏷 管理话题"
2. Type "转子叶尖泄漏" in the input
3. Click "✦ AI 生成并添加"
4. Panel should show loading text, then replace input with a preview card
5. Preview card should show: an editable label, 3-6 English search term chips with ✕ buttons, a hit count, and Cancel/Confirm buttons
6. Clicking ✕ on a term should remove it and update the hit count
7. Clicking "+ 添加" should prompt for a new term and add it
8. Clicking "取消" should restore the input field

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat(topics): add generateTopic, callDeepSeekForTopic, showTopicPreview"
```

---

## Task 9: Confirm adding topic — save, apply overrides, re-render

**File:** `index.html` — JS section, after `cancelTopicPreview()`

**Context:** `confirmAddTopic()` reads the edited label and current terms from the preview card, saves the new topic to `ls_topics`, computes which papers match and adds the label to `ls_topic_overrides`, then re-renders the paper list and tag bar.

- [ ] **Step 1: Add `confirmAddTopic()`**

```javascript
function confirmAddTopic() {
  const preview = document.getElementById('topic-preview');
  if (!preview) return;

  const label = document.getElementById('preview-label-input').value.trim();
  if (!label) {
    document.getElementById('preview-label-input').style.borderColor = 'var(--rel5)';
    return;
  }

  const terms = preview._currentTerms;
  if (!terms || terms.length === 0) {
    alert('至少保留一个搜索词');
    return;
  }

  // Save the new topic
  const topics = getTopics();
  topics.push({ label, terms, builtin: false });
  saveTopics(topics);

  // Apply overrides: find matching papers and add the label
  const overrides = getTopicOverrides();
  papers.forEach(p => {
    if (matchesTopic(p, terms)) {
      if (!overrides[p.id]) overrides[p.id] = [];
      if (!overrides[p.id].includes(label)) {
        overrides[p.id].push(label);
      }
    }
  });
  saveTopicOverrides(overrides);

  // Close preview, restore input
  cancelTopicPreview();

  // Re-render paper list and tag bar
  buildTags();
  render();

  // Re-render the topics panel card list
  renderTopicsPanel();
}
```

- [ ] **Step 2: Verify full add flow**

1. Open browser, click "🏷 管理话题"
2. Type "转子叶尖泄漏", click AI generate, wait for preview
3. Click "确认并更新论文 (N篇)"
4. Verify: topic panel now shows 6 topic cards (5 builtin + 1 new)
5. Verify: new card shows the correct hit count
6. Close topics panel, check tag filter bar — new label should appear as a tag pill
7. Click the new tag pill — papers list should filter to show only matched papers
8. Verify matched paper cards show the new label as a tag
9. Verify `localStorage.getItem('rr_topics')` in console includes the new topic
10. Verify `localStorage.getItem('rr_topic_overrides')` in console contains paper IDs with the new label

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(topics): add confirmAddTopic, save overrides, re-render"
```

---

## Task 10: Delete topic flow

**File:** `index.html` — JS section, after `confirmAddTopic()`

**Context:** `confirmDeleteTopic(idx)` shows the delete confirmation overlay. `closeTopicDeleteOverlay()` dismisses it. The delete action removes the topic from `ls_topics` and removes its label from all entries in `ls_topic_overrides`, then re-renders.

- [ ] **Step 1: Add delete functions**

```javascript
function confirmDeleteTopic(idx) {
  const topics = getTopics();
  const topic = topics[idx];
  if (!topic || topic.builtin) return;

  const overlay = document.getElementById('topic-delete-overlay');
  document.getElementById('topic-delete-msg').textContent =
    `删除「${topic.label}」？将从所有论文移除该标签。`;

  overlay.style.display = 'flex';

  const confirmBtn = document.getElementById('topic-delete-confirm-btn');
  // Remove old listener to avoid stacking
  confirmBtn.replaceWith(confirmBtn.cloneNode(true));
  document.getElementById('topic-delete-confirm-btn').addEventListener('click', () => {
    deleteTopic(idx);
    closeTopicDeleteOverlay();
  });
}

function closeTopicDeleteOverlay() {
  document.getElementById('topic-delete-overlay').style.display = 'none';
}

function deleteTopic(idx) {
  const topics = getTopics();
  const topic = topics[idx];
  if (!topic || topic.builtin) return;

  const label = topic.label;

  // Remove from topics list
  topics.splice(idx, 1);
  saveTopics(topics);

  // Remove label from all overrides
  const overrides = getTopicOverrides();
  Object.keys(overrides).forEach(paperId => {
    overrides[paperId] = overrides[paperId].filter(l => l !== label);
    if (overrides[paperId].length === 0) delete overrides[paperId];
  });
  saveTopicOverrides(overrides);

  // Re-render
  buildTags();
  render();
  renderTopicsPanel();
}
```

- [ ] **Step 2: Verify delete flow**

1. Open browser, add a test topic (e.g., "测试话题") via the AI flow or manually via console:
   ```javascript
   const t = getTopics(); t.push({label:'测试话题',terms:['test'],builtin:false}); saveTopics(t);
   openTopicsPanel();
   ```
2. Expand the "测试话题" card, click "删除话题"
3. Confirmation overlay should appear with correct message
4. Click "取消" — overlay closes, topic remains
5. Re-open delete overlay, click "删除" — overlay closes, card disappears from panel
6. Close panel, verify "测试话题" no longer appears in tag filter bar
7. Verify `localStorage.getItem('rr_topics')` no longer contains the topic

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(topics): add confirmDeleteTopic, deleteTopic, closeTopicDeleteOverlay"
```

---

## Task 11: "同步到流水线" button + `run_pipeline.py` integration

**File:** `index.html` (sync button function) + `scripts/run_pipeline.py` (pipeline reads topics.json)

**Context:** The "↑ 同步到流水线" button commits `data/topics.json` to the repo via GitHub Contents API (same pattern as is already used for understanding pipeline status). `run_pipeline.py` is updated to read `data/topics.json` if it exists, falling back to `config.py`'s `KEYWORDS`.

### Part A: `syncTopicsToPipeline()` in index.html

- [ ] **Step 1: Add `syncTopicsToPipeline()`** in the JS section, after `deleteTopic()`:

```javascript
async function syncTopicsToPipeline() {
  const token = await ensureGithubToken();
  if (!token) return;

  const topics = getTopics();
  const content = JSON.stringify(topics, null, 2);
  const encoded = btoa(unescape(encodeURIComponent(content)));

  // Get current file SHA (needed for update if file exists)
  let sha = null;
  try {
    const getResp = await fetch(
      `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/data/topics.json`,
      { headers: { Authorization: `token ${token}` } }
    );
    if (getResp.ok) {
      const fileData = await getResp.json();
      sha = fileData.sha;
    }
  } catch { /* file doesn't exist yet, sha stays null */ }

  const body = {
    message: 'chore: sync topics from browser',
    content: encoded,
    ...(sha ? { sha } : {})
  };

  const resp = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/data/topics.json`,
    {
      method: 'PUT',
      headers: {
        Authorization: `token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    }
  );

  if (resp.ok) {
    alert('✓ 已同步到仓库 data/topics.json，下次流水线运行时将使用新话题搜索。');
  } else if (resp.status === 401 || resp.status === 403) {
    localStorage.removeItem(LS_GITHUB_TOKEN);
    alert('GitHub Token 无效或权限不足，请重新设置。');
  } else {
    alert('同步失败：HTTP ' + resp.status);
  }
}
```

### Part B: `run_pipeline.py` reads `data/topics.json`

- [ ] **Step 2: Read `run_pipeline.py` to find the `fetch_all_papers()` call** (currently line ~69)

The call at line 69 is: `raw = fetch_all_papers()`. We need to check if `data/topics.json` exists and pass custom keywords to `fetch_all_papers`.

- [ ] **Step 3: Add topic-loading logic in `run_pipeline.py`** — insert before the `raw = fetch_all_papers()` line:

Find this block in `run_pipeline.py`:
```python
    # 1. 抓取原始论文
    raw = fetch_all_papers()
```

Replace with:
```python
    # 1. 抓取原始论文（如果存在 data/topics.json，使用其中的搜索词）
    topics_path = DATA_DIR / "topics.json"
    custom_keywords = None
    if topics_path.exists():
        try:
            topics_data = json.loads(topics_path.read_text(encoding="utf-8"))
            custom_keywords = [term for t in topics_data for term in t.get("terms", [])]
            log.info(f"从 topics.json 加载关键词：{len(custom_keywords)} 个")
        except Exception as e:
            log.warning(f"读取 topics.json 失败，回退到 config.py：{e}")
    raw = fetch_all_papers(keywords=custom_keywords)
```

- [ ] **Step 4: Update `fetch_all_papers()` in `scripts/fetch_papers.py`** to accept an optional `keywords` parameter

Find this function signature (line 117):
```python
def fetch_all_papers() -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = [
        (kw, journal["issn"], journal["name"])
        for journal in TARGET_JOURNALS
        for kw in KEYWORDS
    ]
    log.info(f"并发抓取：{len(tasks)} 个查询（{len(KEYWORDS)} 关键词 × {len(TARGET_JOURNALS)} 期刊）")
```

Replace with:
```python
def fetch_all_papers(keywords=None) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    kw_list = keywords if keywords is not None else KEYWORDS
    tasks = [
        (kw, journal["issn"], journal["name"])
        for journal in TARGET_JOURNALS
        for kw in kw_list
    ]
    log.info(f"并发抓取：{len(tasks)} 个查询（{len(kw_list)} 关键词 × {len(TARGET_JOURNALS)} 期刊）")
```

- [ ] **Step 6: Verify sync button works**

1. Open browser, click "🏷 管理话题"
2. Click "↑ 同步到流水线"
3. If no GitHub token is set, should prompt for one
4. After confirming, should show success alert
5. Check GitHub repo — `data/topics.json` should appear with the current topics

- [ ] **Step 7: Commit**

```bash
cd "E:/claude-project/20260327"
git add index.html scripts/run_pipeline.py scripts/fetch_papers.py
git commit -m "feat(topics): add syncTopicsToPipeline, run_pipeline reads topics.json"
```

---

## Task 12: Edge cases and load() initialization

**File:** `index.html` — `load()` function (line ~2214)

**Context:** On page load, `getTopics()` already initializes `ls_topics` with defaults if empty (implemented in Task 1). But we also need to ensure that if a user reloads the page after adding custom topics, the overrides survive and are reflected in the UI correctly. We verify this and fix the `load()` function to call `buildTags()` after topics are initialized.

- [ ] **Step 1: Verify `load()` already calls `buildTags()`**

Read lines 2214-2237 and confirm `buildTags()` is called after data loads. It should already be there (line ~2233). No change needed if present.

- [ ] **Step 2: Add close-on-overlay-click for topics delete overlay**

Find the `topic-delete-overlay` div in the HTML. Add `onclick` handler to close when clicking the backdrop (but not the dialog itself):

Find this attribute in the topics delete overlay div:
```html
<div id="topic-delete-overlay" style="display:none; position:fixed; inset:0; ...
```

Change it to:
```html
<div id="topic-delete-overlay" onclick="if(event.target===this)closeTopicDeleteOverlay()" style="display:none; position:fixed; inset:0; ...
```

- [ ] **Step 3: Full end-to-end test**

1. Clear localStorage: `localStorage.clear()` in console, refresh page
2. Open topics panel — should show 5 builtin topics with correct hit counts
3. Add a custom topic via AI generation, confirm
4. Refresh page — custom topic should still be in the panel (persisted)
5. Papers matching the custom topic should show its tag (from overrides)
6. Tag filter bar should include the new topic label
7. Delete the custom topic — tag disappears from filter bar and paper cards
8. Refresh — deleted topic stays gone

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(topics): fix delete overlay backdrop click, verify persistence"
```

---

## Task 13: Push and verify on GitHub Pages

- [ ] **Step 1: Push all commits**

```bash
cd "E:/claude-project/20260327"
git push origin main
```

- [ ] **Step 2: Wait for GitHub Pages deploy** (usually 1-2 minutes)

- [ ] **Step 3: Open the live site and run the full end-to-end test** from Task 12, Step 3

- [ ] **Step 4: Verify on live site**
  - Topics panel opens correctly
  - AI generation works (requires DeepSeek key in localStorage)
  - Builtin topics show correct hit counts from real `papers.json`
  - Custom topics persist across page reloads on GitHub Pages
