# Research Radar 🔭

**为特定研究方向定制的文献追踪网站** — 自动从期刊抓取论文，AI 分析摘要，支持标注、课题组追踪和 AI 问答。

> 本项目由 [treeEnergy](https://github.com/treeEnergy) 创建，默认配置针对**压气机气动稳定性**方向（叶尖间隙、机匣处理、进气畸变、稳定性建模），**你可以改成任何研究方向**。

**演示：** https://treeEnergy.github.io/research-radar/

---

## 功能

- 🎨 **双主题**：暖奶白（Anthropic 风格，默认）+ 深色模式，一键切换
- 🔍 **自动抓取**：从 OpenAlex 按 17 个短词关键词 + 6 本期刊（含历史前身）筛选论文
- 🤖 **AI 分析**：DeepSeek 自动生成中文综述、创新点、结论、相关度评分（0-5）
- 💬 **AI 问答**：基于本地论文库的领域专属对话，支持 Markdown 渲染
- 📌 **标注系统**：标记已读、写评价笔记，影响 AI 后续相关度判断
- 👥 **23 个课题组**：基于实际实验室归属（MIT GTL、Cambridge Whittle Lab 等），显示 PI 姓名
- 🗓️ **研究热力图**：1960 年至今，10 个话题 × 5 年间隔，期刊风格绿色渐变色阶，点击查看 AI 综述
- ⚡ **自动更新**：GitHub Actions 每周运行，也支持手动触发
- 📋 **文献愿望清单**：纯本地 localStorage，随时可查

---

## 数据规模

| 指标 | 数量 |
|------|------|
| 当前论文（2020–今） | 500 篇 |
| 历史论文（1960–2019） | 2335 篇 |
| 总计 | **2835 篇** |
| 监控期刊 | 4 本 + 2 本历史前身 |
| 搜索关键词 | 17 个 |
| 研究话题 | 10 个 |
| 追踪课题组 | 23 个 |
| AI 热力图综述 | 130+ 个（5 年 × 话题） |

---

## 部署你自己的版本（5 分钟）

### 前置条件

- GitHub 账号（免费）
- [DeepSeek API Key](https://platform.deepseek.com)（按量计费，几十元可用很久）

### 步骤

**1. Fork 本仓库**

点右上角 **Fork** → 仓库名建议保持 `research-radar`。

**2. 修改检索配置**

编辑 `scripts/config.py`，改成你自己的研究方向：

```python
# 改成你关心的关键词（短词优先，靠 AI 评分过滤）
KEYWORDS = [
    "tip clearance",
    "rotating stall",
    "distortion",
    ...
]

# 改成你关心的期刊（填 ISSN）
TARGET_JOURNALS = [
    {"name": "Journal Name", "issn": "xxxx-xxxx"},
    ...
]

# 改成你关注的课题组
RESEARCH_GROUPS = [
    {"name": "MIT GTL", "institution": "MIT", "pis": ["Greitzer", "Spakovszky"]},
    ...
]
```

**3. 添加 DeepSeek API Key**

进入你 Fork 的仓库 → **Settings → Secrets and variables → Actions → New repository secret**：
- Name: `DEEPSEEK_API_KEY`
- Value: 你的 `sk-xxx`

**4. 启用 GitHub Pages**

进入 **Settings → Pages**：
- Source: `Deploy from a branch`
- Branch: `main` / `/ (root)`
- 点 Save

等 1-2 分钟后访问 `https://你的用户名.github.io/research-radar/`。

**5. 首次抓取论文**

进入 **Actions** 标签页 → 选 "Research Radar Pipeline" → Run workflow。或本地运行：

```bash
cd scripts && python run_pipeline.py
```

**6. 首次使用 AI 对话**

点 AI CHAT 标签页，首次会弹窗要求输入 **DeepSeek API Key**（`sk-` 开头）。

---

## 技术架构

```
GitHub 仓库（静态资源）
├── index.html                      ← 纯前端，无构建工具
├── data/papers.json                ← 近期论文库，最多 500 篇
├── data/papers-historical.json     ← 1960–2019 历史论文（2335 篇）
├── data/timeline.json              ← 热力图：10 话题 × 5 年间隔 + AI 综述
├── data/groups.json                ← 23 个课题组（含 PI 列表）
└── scripts/                        ← Python 抓取 + AI 分析脚本

运行时数据流：
浏览器 → fetch data/*.json       （静态论文数据）
浏览器 → DeepSeek API            （AI 对话，Key 存 localStorage）
GitHub Actions → OpenAlex API   （抓取论文，1960 年至今）
GitHub Actions → DeepSeek API   （AI 分析 + 热力图综述）
GitHub Actions → commit 回仓库  （自动更新数据文件）
```

**所有敏感 Key 仅存在用户浏览器的 localStorage 或 GitHub Secrets 中，不会泄露。**

---

## 自定义

| 想改什么 | 改哪里 |
|----------|--------|
| 搜索关键词 | `scripts/config.py` → `KEYWORDS` |
| 目标期刊 | `scripts/config.py` → `TARGET_JOURNALS` |
| 课题组 | `scripts/config.py` → `RESEARCH_GROUPS` |
| AI 分析提示词 | `scripts/process_with_ai.py` → `SYSTEM_PROMPT` |
| AI 对话提示词 | `index.html` → `CHAT_SYSTEM` |
| 热力图话题 | `scripts/fetch_papers_historical.py` → `DEFAULT_TOPICS` |
| 自动更新频率 | `.github/workflows/pipeline.yml` → `cron` |

---

## 数据说明

- `data/papers.json`：无数量上限，按日期倒序
- `data/papers-historical.json`：1960–2019 历史论文，增量抓取
- `data/timeline.json`：热力图数据 + AI 综述，增量更新
- `data/groups.json`：课题组统计，合并历史 + 当前论文
- 标注/已读/愿望清单存在浏览器 localStorage

---

## 更新日志

### v1.3（2026-03-31）
- **双主题系统**：暖奶白（Anthropic 风格，默认）+ 深色模式，头部 ☀/☽ 切换，偏好持久化
- **Anthropic 设计语言**：Source Serif 4 正文、Inter UI、陶土橙强调色、16px 卡片圆角、反转导航
- **性能优化**：论文列表分页（80 篇/批），主题切换零延迟
- **视觉优化**：深色可读文字、13px 热力图数字、Markdown 渲染 AI 综述
- **代码审查**：修复 XSS、去重函数、导入顺序、PI 匹配逻辑
- **项目手册**：`docs/manual.md`，10 章节完整文档

### v1.2（2026-03-30）
- **热力图重设计**：5 年间隔，左右分栏布局，期刊风格绿色渐变色阶，双行表头（年代 + 细分）
- **课题组合并**：55 个自动识别 → 23 个人工策展，显示 PI 姓名，按实验室归属分组
- **搜索关键词重构**：长词 → 短词优先，论文库从 400 篇增至 2835 篇
- **1960s 覆盖**：新增 J. Eng. for Power 和 J. Basic Engineering 两本历史期刊
- **AI 对话 Markdown 渲染**、**相关度排序**

### v1.1（2026-03-30）
- 新增时间轴热力图、文献愿望清单、历史论文抓取

### v1.0（2026-03-28）
- 初始发布：论文抓取、AI 分析、课题组追踪、标注系统、AI 问答

---

## License

MIT — 自由使用、修改、分发。
