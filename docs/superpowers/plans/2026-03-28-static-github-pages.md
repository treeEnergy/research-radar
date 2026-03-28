# Research Radar 静态化迁移至 GitHub Pages 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Research Radar 从 Flask 本地服务器迁移为托管在 GitHub Pages 上的纯静态网站，所有写操作改用 localStorage，AI 对话直接调 DeepSeek API，流水线触发改用 GitHub Actions API。

**Architecture:** `index.html` 直接 fetch 静态 JSON 文件；标注/课题组数据存 localStorage；DeepSeek API Key 和 GitHub Token 首次使用时由用户填入并存 localStorage；GitHub Actions workflow 定时或手动触发后自动 commit 更新的数据文件。

**Tech Stack:** 纯 HTML/CSS/JavaScript（无构建工具）、GitHub Actions、DeepSeek API、GitHub REST API

---

## 文件改动总览

| 文件 | 操作 |
|------|------|
| `index.html` | 修改：替换所有 `/api/` 调用（约 9 处），新增配置块、localStorage 工具函数、设置弹窗 |
| `.github/workflows/pipeline.yml` | 新增：定时 + 手动触发的 Actions workflow |
| `scripts/requirements.txt` | 修改：删除 `flask` 行 |
| `scripts/server.py` | 删除 |

---

## Task 1：在 index.html 顶部添加配置常量和 localStorage 工具函数

**Files:**
- Modify: `index.html`（在现有 `<script>` 标签开头插入）

在 `index.html` 里找到 `<script>` 标签的开始（紧接着 `</style>` 后），在变量声明 `let papers = []...` 之前插入以下代码块。

- [ ] **Step 1: 找到插入位置**

在 `index.html` 第 2130 行附近，`let papers = [], repos = []...` 这行的上方。

- [ ] **Step 2: 插入配置常量和工具函数**

```js
// ── 静态站配置（部署前修改这两行）──────────────────
const GITHUB_OWNER = 'your-username';   // ← 改成你的 GitHub 用户名
const GITHUB_REPO  = 'research-radar';  // ← 改成你的仓库名
// ──────────────────────────────────────────────────

// localStorage 键名
const LS_ANNOTATIONS   = 'rr_annotations';
const LS_CUSTOM_GROUPS = 'rr_custom_groups';
const LS_DEEPSEEK_KEY  = 'rr_deepseek_key';
const LS_GITHUB_TOKEN  = 'rr_github_token';

// localStorage 工具函数
function lsGet(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}
function lsSet(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function getAnnotations()       { return lsGet(LS_ANNOTATIONS, {}); }
function saveAnnotations(data)  { lsSet(LS_ANNOTATIONS, data); }
function getCustomGroups()      { return lsGet(LS_CUSTOM_GROUPS, []); }
function saveCustomGroups(data) { lsSet(LS_CUSTOM_GROUPS, data); }
```

- [ ] **Step 3: 验证**

用浏览器打开 `index.html`（或 `python -m http.server 8000` 然后访问 localhost:8000），打开开发者工具 Console，输入 `getAnnotations()` 应返回 `{}`，输入 `GITHUB_OWNER` 应返回 `'your-username'`。

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add localStorage utils and config constants"
```

---

## Task 2：添加首次使用设置弹窗（DeepSeek Key + GitHub Token）

**Files:**
- Modify: `index.html`（HTML 部分加弹窗，JS 部分加 `getApiKey()` / `getGithubToken()` 函数）

设置弹窗在用户首次点击"AI 对话"或"触发流水线"时弹出，填入后存 localStorage，下次无需再填。

- [ ] **Step 1: 在 `</body>` 前插入设置弹窗 HTML**

```html
<!-- 设置弹窗 -->
<div id="settings-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9000;display:none;align-items:center;justify-content:center;">
  <div style="background:var(--surface);border:1px solid var(--border2);border-radius:8px;padding:32px;width:420px;max-width:90vw;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--gold);letter-spacing:.1em;margin-bottom:20px;" id="settings-title">SETTINGS</div>
    <div id="settings-body"></div>
    <div style="display:flex;gap:12px;margin-top:24px;justify-content:flex-end;">
      <button onclick="closeSettings()" style="background:transparent;border:1px solid var(--border2);color:var(--text3);padding:8px 18px;border-radius:4px;cursor:pointer;font-family:'IBM Plex Mono',monospace;font-size:12px;">取消</button>
      <button onclick="confirmSettings()" style="background:var(--gold);border:none;color:#111;padding:8px 18px;border-radius:4px;cursor:pointer;font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:600;">保存</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: 在 JS 中添加弹窗控制函数**

在 Task 1 插入的代码块之后继续添加：

```js
// ── 设置弹窗 ─────────────────────────────────────
let _settingsResolve = null;

function promptForKey(title, storageKey, placeholder) {
  return new Promise(resolve => {
    _settingsResolve = resolve;
    const overlay = document.getElementById('settings-overlay');
    document.getElementById('settings-title').textContent = title;
    document.getElementById('settings-body').innerHTML = `
      <input id="settings-input" type="password"
        placeholder="${placeholder}"
        style="width:100%;background:var(--bg);border:1px solid var(--border2);border-radius:4px;
               padding:10px 14px;color:var(--text);font-family:'IBM Plex Mono',monospace;font-size:13px;outline:none;"
        value="${localStorage.getItem(storageKey) || ''}" />
      <div style="margin-top:8px;font-size:12px;color:var(--text3);">仅存在本浏览器，不会上传到任何服务器。</div>`;
    overlay.style.display = 'flex';
    document.getElementById('settings-input').focus();
    overlay._storageKey = storageKey;
  });
}

function confirmSettings() {
  const input = document.getElementById('settings-input');
  const val = input.value.trim();
  const key = document.getElementById('settings-overlay')._storageKey;
  if (val) localStorage.setItem(key, val);
  closeSettings();
  if (_settingsResolve) { _settingsResolve(val); _settingsResolve = null; }
}

function closeSettings() {
  document.getElementById('settings-overlay').style.display = 'none';
  if (_settingsResolve) { _settingsResolve(null); _settingsResolve = null; }
}

// 确保已有 key，否则弹窗请求输入
async function ensureDeepseekKey() {
  let key = localStorage.getItem(LS_DEEPSEEK_KEY);
  if (!key) key = await promptForKey('DEEPSEEK API KEY', LS_DEEPSEEK_KEY, 'sk-xxxxxxxxxxxxxxxx');
  return key;
}

async function ensureGithubToken() {
  let token = localStorage.getItem(LS_GITHUB_TOKEN);
  if (!token) token = await promptForKey('GITHUB TOKEN (workflow 权限)', LS_GITHUB_TOKEN, 'github_pat_xxxx');
  return token;
}
```

- [ ] **Step 3: 验证弹窗**

刷新页面，在 Console 运行 `promptForKey('TEST', 'test_key', 'input here')`，应弹出输入框，填入内容点保存后 `localStorage.getItem('test_key')` 能读到值，点取消 Promise resolve 为 null。

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add first-run settings modal for API keys"
```

---

## Task 3：替换 load() 中的 `/api/annotations` 和 `/api/groups/custom`

**Files:**
- Modify: `index.html` 第 2136–2163 行（`load()` 函数）

- [ ] **Step 1: 替换 load() 中的两个 fetch 调用**

找到 load() 函数中的这段：
```js
const [p, r, m, g, a, cg] = await Promise.allSettled([
    fetch('data/papers.json').then(x => x.json()),
    fetch('data/repos.json').then(x => x.json()),
    fetch('data/meta.json').then(x => x.json()),
    fetch('data/groups.json').then(x => x.json()),
    fetch('/api/annotations').then(x => x.json()),
    fetch('/api/groups/custom').then(x => x.json()),
  ]);
```

替换为：
```js
const [p, r, m, g] = await Promise.allSettled([
    fetch('data/papers.json').then(x => x.json()),
    fetch('data/repos.json').then(x => x.json()),
    fetch('data/meta.json').then(x => x.json()),
    fetch('data/groups.json').then(x => x.json()),
  ]);
```

- [ ] **Step 2: 替换 a、cg 的赋值行**

找到：
```js
  customGroups = cg.status === 'fulfilled' ? cg.value : [];
  annotations = a.status === 'fulfilled' ? a.value : {};
```

替换为：
```js
  customGroups = getCustomGroups();
  annotations  = getAnnotations();
```

- [ ] **Step 3: 删除页面加载时的 pipeline 状态检查**

找到并删除以下整段（约第 2162–2175 行）：
```js
  // 页面加载时检查 pipeline 是否正在运行
  const ps = await fetch('/api/pipeline/status').then(r => r.json()).catch(() => null);
  if (ps && ps.running) {
    const btn = document.getElementById('run-btn');
    setBtnRunning(btn);
    // 用已有日志初始化面板 UI，不重置步骤
    document.getElementById('pipeline-title').textContent = 'PIPELINE RUNNING';
    document.getElementById('pipeline-spinner').textContent = '⟳';
    ...（整个 if 块）
  }
```

（GitHub Pages 是静态的，刷新后无法恢复正在运行的流水线状态，直接删除即可。）

- [ ] **Step 4: 验证**

浏览器打开页面，论文正常显示，标注/课题组从 localStorage 加载（初始为空，不报错）。Console 无 `/api/` 请求。

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: replace annotations and groups API calls with localStorage"
```

---

## Task 4：替换标注 API 调用（saveAnnotation / clearAnnotation / toggleRead）

**Files:**
- Modify: `index.html`（约第 2483–2520 行，三处 `/api/annotate` 调用）

- [ ] **Step 1: 替换 saveAnnotation 函数**

找到：
```js
  const resp = await fetch('/api/annotate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ paper_id: id, note: note }),
  });
  const data = await resp.json();
```

替换为：
```js
  const anns = getAnnotations();
  const entry = anns[id] || {};
  if (note) {
    entry.note    = note;
    entry.updated = new Date().toISOString();
  } else {
    delete entry.note;
    delete entry.updated;
  }
  if (Object.keys(entry).length) anns[id] = entry;
  else delete anns[id];
  saveAnnotations(anns);
  const data = { ok: true, entry };
```

- [ ] **Step 2: 替换 clearAnnotation 函数**

找到：
```js
  await fetch('/api/annotate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ paper_id: id, note: '' }),
  });
```

替换为：
```js
  const anns = getAnnotations();
  if (anns[id]) { delete anns[id].note; delete anns[id].updated; }
  if (anns[id] && !Object.keys(anns[id]).length) delete anns[id];
  saveAnnotations(anns);
```

- [ ] **Step 3: 替换 toggleRead 函数**

找到：
```js
  await fetch('/api/annotate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ paper_id: id, read: isRead }),
  });
```

替换为：
```js
  const anns = getAnnotations();
  const entry = anns[id] || {};
  if (isRead) { entry.read = true; entry.read_at = new Date().toISOString(); }
  else { delete entry.read; delete entry.read_at; }
  if (Object.keys(entry).length) anns[id] = entry;
  else delete anns[id];
  saveAnnotations(anns);
```

- [ ] **Step 4: 验证**

在页面上给一篇论文写评价、标记已读，刷新页面后状态仍然保留。Console 无 `/api/` 请求。

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: replace annotate API calls with localStorage"
```

---

## Task 5：替换课题组 API 调用（groups/save、groups/delete）

**Files:**
- Modify: `index.html`（约第 2432、2451 行）

- [ ] **Step 1: 替换 groups/save**

找到：
```js
  const res = await fetch('/api/groups/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name, institution, pis: pisRaw, replaces }),
  });
  const data = await res.json();
```

替换为：
```js
  const pis = pisRaw.replace(/，/g, ',').split(',').map(p => p.trim()).filter(Boolean);
  let groups_list = getCustomGroups();
  groups_list = groups_list.filter(g => g.name !== name && g.replaces !== replaces);
  const entry_g = { name, institution, pis, custom: true };
  if (replaces) entry_g.replaces = replaces;
  groups_list.push(entry_g);
  saveCustomGroups(groups_list);
  const data = { ok: true };
```

- [ ] **Step 2: 替换 groups/delete**

找到：
```js
  await fetch('/api/groups/delete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name }),
  });
```

替换为：
```js
  let groups_list = getCustomGroups();
  groups_list = groups_list.filter(g => g.name !== name);
  saveCustomGroups(groups_list);
```

- [ ] **Step 3: 同步更新内存中的 customGroups 变量**

两处替换后，原来代码后面可能有 `customGroups = ...` 的重新加载，确认是否有；如有则改为：
```js
  customGroups = getCustomGroups();
```

- [ ] **Step 4: 验证**

在页面上新增/编辑/删除自定义课题组，刷新页面后修改仍存在。Console 无 `/api/` 请求。

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: replace groups API calls with localStorage"
```

---

## Task 6：替换 AI 对话（直接调 DeepSeek API + JS 版论文检索）

**Files:**
- Modify: `index.html`（约第 2893–2951 行，`sendChat()` 函数）

- [ ] **Step 1: 在 Task 1 的工具函数块后添加 JS 版论文检索函数**

```js
// ── JS 版论文本地检索（移植自 server.py _search_papers_local）──
function searchPapersLocal(query, topK = 12) {
  const q = query.toLowerCase();
  const enWords = q.split(/\s+/).filter(w => w.length > 2 && /^[a-z0-9]+$/.test(w));
  const zhWords = (q.match(/[\u4e00-\u9fff]{2,}/g) || []);
  const keywords = [...enWords, ...zhWords];
  if (!keywords.length) return [];

  const scored = [];
  for (const p of papers) {
    const text = [
      p.title || '',
      (p.abstract || '').slice(0, 500),
      p.summary_zh || '',
      p.method || '',
      p.innovation || '',
      (p.tags || []).join(' '),
      (p.authors || []).slice(0, 3).join(' '),
    ].join(' ').toLowerCase();

    const kwScore = keywords.reduce((s, kw) => {
      const count = (text.match(new RegExp(kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
      return s + count * (/^[a-z0-9]+$/.test(kw) ? 2 : 1);
    }, 0);
    if (!kwScore) continue;
    scored.push([kwScore * 10 + (p.relevance || 0), p]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  return scored.slice(0, topK).map(x => x[1]);
}
```

- [ ] **Step 2: 替换 sendChat() 中的 fetch('/api/chat', ...) 调用**

找到并替换整个 try 块（约第 2894–2955 行）：

```js
  try {
    const apiKey = await ensureDeepseekKey();
    if (!apiKey) { thinkingEl.remove(); chatBusy = false; btn.disabled = false; return; }

    // 本地检索相关论文
    const relevant = searchPapersLocal(msg);
    const authorCounter = {};
    for (const p of papers) (p.authors || []).forEach(a => authorCounter[a] = (authorCounter[a]||0)+1);
    const topAuthors = Object.entries(authorCounter).sort((a,b)=>b[1]-a[1]).slice(0,30)
      .map(([a,c]) => `${a}（${c}篇）`).join(', ');
    const relDist = papers.reduce((d,p) => { d[p.relevance||0]=(d[p.relevance||0]||0)+1; return d; }, {});
    const libSummary = `论文库概况：共 ${papers.length} 篇，` +
      `相关度分布：5分=${relDist[5]||0}篇 4分=${relDist[4]||0}篇 3分=${relDist[3]||0}篇 2分=${relDist[2]||0}篇。\n` +
      `高频作者（前30）：${topAuthors}`;

    let contextParts = [libSummary];
    if (relevant.length) {
      const lines = relevant.map(p => {
        const parts = [`【${p.title}】(${(p.date||'').slice(0,4)}, 相关度${p.relevance||'?'}, ${p.venue||''})`];
        parts.push(`  作者: ${(p.authors||[]).join(', ')}`);
        parts.push(`  中文综述: ${p.summary_zh||''}`);
        if (p.method)       parts.push(`  研究方法: ${p.method}`);
        if (p.innovation)   parts.push(`  创新点: ${p.innovation}`);
        if (p.conclusions)  parts.push(`  主要结论: ${p.conclusions}`);
        if (p.tags?.length) parts.push(`  标签: ${p.tags.join(', ')}`);
        return parts.join('\n');
      });
      contextParts.push('以下是与当前问题最相关的论文：\n\n' + lines.join('\n\n'));
    }

    const CHAT_SYSTEM = `你是一个航空发动机压气机气动热力学领域的研究助手。
用户的研究方向：压气机稳定性、叶尖间隙、机匣处理、进气畸变、稳定性建模（激盘/体力模型）。
你有权访问用户的论文库（已在下方提供相关论文摘要）。
优先基于论文库回答问题，不要编造不在库中的论文信息。
如果论文库中没有找到相关内容，明确告知用户，并建议他们使用"更新检索"抓取更多论文。
回答简洁、专业，使用中文，可适当引用论文标题。`;

    const messages = [
      { role: 'system', content: CHAT_SYSTEM },
      { role: 'system', content: contextParts.join('\n\n') },
      ...chatHistory.slice(-6),
      { role: 'user', content: msg },
    ];

    // 先渲染 meta（检索到的论文）
    const sources = relevant.map(p => p.title.slice(0, 60));
    thinkingEl.remove();
    aiTextEl = appendChatMsg('assistant', '', sources);
    const cursor = document.createElement('span');
    cursor.className = 'chat-cursor';
    aiTextEl.after(cursor);

    const resp = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
      body: JSON.stringify({ model: 'deepseek-chat', messages, stream: true, temperature: 0.3, max_tokens: 1200 }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      cursor.remove();
      appendChatMsg('assistant', '错误：' + (err.error?.message || resp.statusText));
      chatBusy = false; btn.disabled = false; return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') { cursor.remove(); chatHistory.push({ role: 'assistant', content: aiText }); break; }
        try {
          const delta = JSON.parse(raw).choices?.[0]?.delta?.content || '';
          if (delta) {
            aiText += delta;
            if (aiTextEl) {
              aiTextEl.textContent = aiText;
              document.getElementById('chat-messages').scrollTop = 99999;
            }
          }
        } catch {}
      }
    }
  } catch (e) {
    thinkingEl?.remove();
    appendChatMsg('assistant', '网络错误：' + e.message);
  }
```

- [ ] **Step 3: 验证**

打开 AI 对话面板，首次发送消息时弹出 DeepSeek Key 输入框，填入后正常流式返回回答，论文来源显示正确。再次发送消息不再弹窗。

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: replace chat API with direct DeepSeek SSE call"
```

---

## Task 7：替换流水线 API 调用（GitHub Actions dispatch + 状态轮询）

**Files:**
- Modify: `index.html`（`runPipeline()` 和 `startPolling()` 函数）

- [ ] **Step 1: 替换 runPipeline() 函数**

找到并完整替换 `async function runPipeline()` 函数：

```js
async function runPipeline() {
  const btn = document.getElementById('run-btn');
  const token = await ensureGithubToken();
  if (!token) return;

  // 触发 GitHub Actions workflow dispatch
  const resp = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/pipeline.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: 'main' }),
    }
  );

  if (resp.status === 401 || resp.status === 403) {
    localStorage.removeItem(LS_GITHUB_TOKEN);
    appendPipelineLog('Token 无效或权限不足，请重新输入。');
    return;
  }
  if (!resp.ok && resp.status !== 204) {
    appendPipelineLog(`触发失败（HTTP ${resp.status}），请检查 Token 和仓库名。`);
    return;
  }

  setBtnRunning(btn);
  initPanelUI();
  openPipelinePanel();
  // 等 3 秒让 Actions 产生 run 记录，再开始轮询
  setTimeout(() => startPolling(btn), 3000);
}
```

- [ ] **Step 2: 替换 startPolling() 函数**

找到并完整替换 `function startPolling(btn)` 函数：

```js
function startPolling(btn) {
  if (_pipelinePoll) return;
  const token = localStorage.getItem(LS_GITHUB_TOKEN);

  _pipelinePoll = setInterval(async () => {
    try {
      const r = await fetch(
        `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs?per_page=5`,
        { headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/vnd.github+json' } }
      );
      const data = await r.json();
      const run = (data.workflow_runs || []).find(r =>
        r.name === 'Research Radar Pipeline' || r.path?.includes('pipeline.yml')
      );
      if (!run) return;  // 还没出现，继续等

      const status   = run.status;    // queued / in_progress / completed
      const conclusion = run.conclusion; // success / failure / null
      const runUrl   = run.html_url;

      const STATUS_ZH = { queued: '排队中…', in_progress: '运行中…', completed: conclusion === 'success' ? '完成 ✓' : `失败（${conclusion}）` };
      const logEl = document.getElementById('pipeline-log');
      logEl.textContent = `GitHub Actions 状态：${STATUS_ZH[status] || status}\n\n详细日志：${runUrl}`;
      if (logEl.style.display !== 'none') logEl.scrollTop = logEl.scrollHeight;

      const isRunning = status !== 'completed';
      updateStepUI([], isRunning, isRunning ? 'running' : (conclusion === 'success' ? 'done' : 'error'));

      if (!isRunning) {
        clearInterval(_pipelinePoll);
        _pipelinePoll = null;
        setBtnIdle(btn || document.getElementById('run-btn'));
        document.getElementById('pipeline-spinner').textContent = conclusion === 'success' ? '✓' : '✗';
        document.getElementById('pipeline-spinner').style.animation = '';
        document.getElementById('pipeline-title').textContent =
          conclusion === 'success' ? 'PIPELINE COMPLETE' : 'PIPELINE ERROR';
        document.getElementById('pipeline-reload-btn').style.display = conclusion === 'success' ? '' : 'none';
      }
    } catch (e) {
      appendPipelineLog('轮询失败：' + e.message);
    }
  }, 3000);
}
```

- [ ] **Step 3: 添加 appendPipelineLog 辅助函数**

在 `startPolling` 函数之后添加：

```js
function appendPipelineLog(msg) {
  const logEl = document.getElementById('pipeline-log');
  if (logEl) logEl.textContent += '\n' + msg;
}
```

- [ ] **Step 4: 验证**

点击"更新检索"按钮，应弹出 GitHub Token 输入框，填入后触发（返回 204）。流水线面板打开，3 秒后开始轮询，状态更新为"排队中"→"运行中"→"完成"。

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: replace pipeline API with GitHub Actions dispatch and polling"
```

---

## Task 8：创建 GitHub Actions Workflow 文件

**Files:**
- Create: `.github/workflows/pipeline.yml`

- [ ] **Step 1: 创建目录和文件**

```bash
mkdir -p .github/workflows
```

内容如下：

```yaml
name: Research Radar Pipeline

on:
  schedule:
    - cron: '0 2 * * 1'   # 每周一 UTC 02:00 自动运行
  workflow_dispatch:        # 支持手动触发 / API 触发

permissions:
  contents: write           # 允许 commit 回 papers.json

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r scripts/requirements.txt

      - name: Run pipeline
        run: cd scripts && python run_pipeline.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}

      - name: Commit updated data
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "auto: update papers data [skip ci]"
          file_pattern: data/papers.json data/repos.json data/groups.json data/meta.json
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/pipeline.yml
git commit -m "feat: add GitHub Actions workflow for pipeline"
```

---

## Task 9：清理 server.py 和 requirements.txt

**Files:**
- Delete: `scripts/server.py`
- Modify: `scripts/requirements.txt`（删除 `flask` 行）

- [ ] **Step 1: 从 requirements.txt 删除 flask**

将 `scripts/requirements.txt` 内容改为：
```
requests
openai
python-dotenv
pdfplumber
```

- [ ] **Step 2: 删除 server.py**

```bash
rm scripts/server.py
```

- [ ] **Step 3: Commit**

```bash
git add scripts/requirements.txt
git rm scripts/server.py
git commit -m "chore: remove Flask server, update requirements"
```

---

## Task 10：设置 GitHub 仓库并启用 GitHub Pages

这是手动操作步骤，不涉及代码。

- [ ] **Step 1: 修改 index.html 顶部的配置常量**

将 Task 1 中插入的常量改为实际值：
```js
const GITHUB_OWNER = '你的GitHub用户名';
const GITHUB_REPO  = '你的仓库名';
```

- [ ] **Step 2: 创建 GitHub 仓库并推送**

```bash
git init   # 如果尚未 init
git remote add origin https://github.com/你的用户名/你的仓库名.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: 在 GitHub 仓库 Settings 中配置 Secrets**

进入仓库 → Settings → Secrets and variables → Actions → New repository secret：
- Name: `DEEPSEEK_API_KEY`
- Value: 你的 DeepSeek API Key（`sk-xxx`）

- [ ] **Step 4: 启用 GitHub Pages**

进入仓库 → Settings → Pages：
- Source: `Deploy from a branch`
- Branch: `main` / `/ (root)`
- 点 Save

几分钟后访问 `https://你的用户名.github.io/你的仓库名/` 即可看到网站。

- [ ] **Step 5: 创建 GitHub Personal Access Token**

进入 GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens：
- Repository access: 选择你的仓库
- Permissions → Actions: Read and write
- 生成并复制 token

首次在网页上点"更新检索"时填入此 token。

- [ ] **Step 6: 验证全流程**

访问 GitHub Pages 链接，确认：
- [ ] 论文列表正常加载
- [ ] 标注/已读功能正常（刷新后保留）
- [ ] 自定义课题组编辑正常（刷新后保留）
- [ ] AI 对话正常（首次填入 DeepSeek Key）
- [ ] 触发流水线正常（首次填入 GitHub Token，Actions 页面有新 run 出现）
- [ ] 流水线完成后约 1-2 分钟，页面重新加载数据更新
