# Keyword / Topic Management — Design Spec

**Date:** 2026-03-28
**Status:** Approved

---

## Goal

Allow users to add and remove research topics (keywords) directly in the webpage, without editing `config.py` or pushing code. AI generates English search terms from a Chinese or English topic name. Changes take effect immediately on existing papers (local keyword match) and are picked up by the next pipeline run for new papers.

---

## Architecture

### Data Storage

Topics are stored in `localStorage` under key `ls_topics`. Structure:

```json
[
  {
    "label": "叶尖间隙",
    "terms": ["compressor tip clearance", "tip clearance effect", "non-axisymmetric tip clearance"],
    "builtin": true
  },
  {
    "label": "转子叶尖泄漏",
    "terms": ["rotor tip leakage", "tip leakage vortex", "tip clearance flow"],
    "builtin": false
  }
]
```

- `label`: Chinese display name shown on paper tags
- `terms`: English search terms used for local matching and pipeline queries
- `builtin`: `true` for topics seeded from `config.py` defaults — these cannot be deleted

**Initialization:** On first load, if `ls_topics` is empty, seed with a hardcoded default list matching the current `config.py` keywords.

### Pipeline Integration

The pipeline reads topics from `data/topics.json` (committed to repo). A separate "Export topics" action (or manual step) writes `localStorage` topics to this file via GitHub API commit. On next pipeline run, `run_pipeline.py` reads `data/topics.json` instead of `config.py` keywords (falls back to `config.py` if file absent).

---

## UI

### Entry Point

Top bar: add a `🏷 管理话题` button next to the existing `▶ 更新检索` button. Clicking it opens a right-side slide panel (same pattern as existing settings modal).

### Panel Layout (C2 — Card Expansion)

```
┌─────────────────────────────┐
│ 话题管理                     │  ← panel header
│ 管理研究关键词，自动更新论文分类 │
├─────────────────────────────┤
│ 当前话题 · N个               │
│                             │
│ ┌─────────────────────────┐ │
│ │ 叶尖间隙          47篇 › │ │  ← collapsed card
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 机匣处理          31篇   │ │  ← expanded card
│ │ [compressor tip…] [✕]   │ │
│ │ [tip clearance…]  [✕]   │ │
│ │ [+ 添加搜索词]           │ │
│ │                      [✕]│ │  ← delete topic (non-builtin only)
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ 添加新话题                   │
│ [输入话题名…        ]        │
│ [✦ AI 生成并添加]            │
└─────────────────────────────┘
```

- Each card shows: label, hit count (papers matching any term), expand/collapse toggle
- Expanded card shows all search terms as removable chips + "添加搜索词" chip
- Non-builtin topics show a ✕ delete button in the expanded card header
- Builtin topics show a lock icon, no delete button

### Add Topic Flow (Y — Preview/Confirm)

1. User types topic name (Chinese or English) in input field
2. Clicks "✦ AI 生成并添加"
3. Button becomes loading state, calls DeepSeek API
4. **Preview card appears** (replaces input area):
   - Editable label name field
   - Search term chips with ✕ to remove each
   - "+ 添加" chip to add custom terms
   - "预计命中现有论文: N 篇" (computed from local keyword match, updates live as terms change)
   - `[取消]` and `[确认并更新论文 (N篇)]` buttons
5. On confirm:
   - Save topic to `localStorage`
   - Run local keyword match on all papers in memory → add new label to matching papers
   - Update paper annotations in `localStorage` (tag additions are stored separately from AI-assigned tags — stored under `ls_topic_overrides`)
   - Re-render paper list
   - Collapse preview, show new topic card in list

### Delete Topic Flow

1. Click ✕ on expanded card → confirmation dialog: "删除「叶尖间隙」？将从所有论文移除该标签。"
2. Confirm → remove topic from `localStorage` → remove label from all papers in memory → re-render

---

## Local Keyword Match

```
matchesTopic(paper, terms) → bool
```

For each term in `terms`, do case-insensitive substring match against:
- `paper.title`
- `paper.abstract`
- `paper.keywords` (array, joined)

If any term matches any field → `true`.

Hit count shown in card header = `papers.filter(p => matchesTopic(p, topic.terms)).length`.

---

## DeepSeek API Call

**Prompt:**

```
你是一个学术文献检索专家。用户输入一个研究话题，请生成：
1. 中文标签名（简短，2-6个汉字）
2. 3-6个英文搜索词（用于学术数据库检索，覆盖该话题的主要变体表达）

话题：{input}

以 JSON 格式返回，不要有其他内容：
{"label": "...", "terms": ["...", "...", "..."]}
```

Parse JSON from response. If parsing fails, show error and allow retry.

---

## Paper Tag Storage

AI-assigned tags live in `papers.json` (immutable from browser). User-added topic matches are stored in `localStorage` under `ls_topic_overrides`:

```json
{
  "paper_id_123": ["转子叶尖泄漏", "叶尖间隙"],
  "paper_id_456": ["进气畸变"]
}
```

When rendering paper tags, merge `paper.topics` (from JSON) with `ls_topic_overrides[paper.id]` (from localStorage), deduplicated.

When a topic is deleted, remove its label from all entries in `ls_topic_overrides`.

---

## Pipeline Integration Detail

`run_pipeline.py` change:
- If `data/topics.json` exists → read `terms` from all topics → use as keyword list for OpenAlex queries
- Else → fall back to `KEYWORDS` in `config.py`

The user can sync their localStorage topics to `data/topics.json` via a "同步到流水线" button in the panel, which commits the file via GitHub API (requires GitHub token already stored in localStorage).

---

## Error Handling

- DeepSeek call fails → show inline error "AI 生成失败，请重试" with retry button
- JSON parse fails → show raw response + "请手动输入搜索词" fallback (show plain input)
- No DeepSeek key → prompt user for key (same flow as chat feature)

---

## Out of Scope

- Editing existing topics' labels (post-add)
- Reordering topics
- Bulk import/export
- Real-time collaboration across devices (localStorage is device-local)
