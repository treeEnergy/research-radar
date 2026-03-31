# Research Radar 工作手册

> 版本 1.2 | 2026-03-31 更新

---

## 1. 系统概述

Research Radar 是一个面向特定研究方向的学术文献自动追踪与分析系统。默认配置针对**压气机气动稳定性**方向，覆盖叶尖间隙、机匣处理、进气畸变、稳定性建模等子领域。

**核心能力：**
- 自动从 OpenAlex 抓取 6 本期刊（含 2 本历史前身）的论文
- DeepSeek AI 生成中文综述、研究方法、创新点、结论、相关度评分
- 1960 年至今的研究趋势热力图（10 话题 × 5 年间隔）
- 23 个课题组追踪（MIT GTL、Cambridge Whittle Lab 等）
- 基于论文库的 AI 对话问答
- GitHub Actions 自动更新 + GitHub Pages 静态部署

---

## 2. 项目结构

```
research-radar/
├── index.html                          # 前端（纯 HTML/CSS/JS，~4200 行）
├── data/
│   ├── papers.json                     # 2020 年至今论文（无上限）
│   ├── papers-historical.json          # 1960–2019 历史论文（~2335 篇）
│   ├── timeline.json                   # 热力图数据 + AI 综述
│   ├── groups.json                     # 课题组统计
│   ├── repos.json                      # GitHub 仓库
│   ├── meta.json                       # 最后更新时间
│   ├── annotations.json                # （已弃用，标注迁移至 localStorage）
│   └── custom_groups.json              # 用户自定义课题组
├── scripts/
│   ├── config.py                       # 关键词、期刊、课题组配置
│   ├── run_pipeline.py                 # 主流水线入口
│   ├── fetch_papers.py                 # OpenAlex 抓取（8 线程并发）
│   ├── fetch_papers_historical.py      # 历史论文抓取（1960–2019）
│   ├── build_timeline.py              # 热力图数据生成
│   ├── process_with_ai.py             # DeepSeek AI 分析（5 线程并发）
│   ├── fetch_repos.py                 # GitHub 仓库抓取
│   ├── backfill_authors.py            # 一次性工具（已完成）
│   └── requirements.txt               # Python 依赖
├── .github/workflows/
│   └── pipeline.yml                    # GitHub Actions 自动流水线
├── CLAUDE.md                           # Claude Code 项目说明
└── README.md                           # 项目介绍
```

---

## 3. 环境配置

### 3.1 Python 环境

```bash
cd scripts
pip install -r requirements.txt
```

依赖：`requests`, `python-dotenv`, `openai`（用于 DeepSeek API）

### 3.2 环境变量

在项目根目录创建 `.env`（已加入 .gitignore）：

```
DEEPSEEK_API_KEY=sk-你的密钥
GITHUB_TOKEN=ghp_你的token（可选，用于抓取 GitHub 仓库）
```

获取 DeepSeek API Key：https://platform.deepseek.com → API Keys

### 3.3 GitHub 配置（线上部署）

1. **Secrets**：Settings → Secrets → Actions → 添加 `DEEPSEEK_API_KEY`
2. **Pages**：Settings → Pages → Source: `main` branch, `/ (root)`
3. **Actions**：自动每周一 UTC 02:00 运行，也可手动触发

---

## 4. 数据流水线

### 4.1 完整流水线

```bash
cd scripts && python run_pipeline.py
```

执行顺序：
1. **抓取论文** → `fetch_papers.py`，17 个关键词 × 4 本期刊，8 线程并发
2. **AI 分析** → `process_with_ai.py`，DeepSeek 生成结构化分析，5 线程并发
3. **写入数据** → 合并新旧论文，按日期倒序，匹配课题组标签
4. **抓取仓库** → `fetch_repos.py`，GitHub API 搜索相关仓库
5. **历史论文** → `fetch_papers_historical.py`，增量抓取 1960–2019
6. **热力图** → `build_timeline.py`，统计话题 × 5 年，增量生成 AI 综述

### 4.2 单独运行各模块

```bash
# 只抓取论文（不做 AI 分析）
python fetch_papers.py

# 只跑 AI 分析
python process_with_ai.py

# 只更新历史论文
python -c "from fetch_papers_historical import fetch_papers_historical_incremental; fetch_papers_historical_incremental()"

# 只重建热力图（需要 DEEPSEEK_API_KEY 环境变量）
python -c "from build_timeline import build_timeline; build_timeline()"
```

### 4.3 流水线输出

| 文件 | 内容 | 更新方式 |
|------|------|----------|
| `papers.json` | 2020 至今论文（含 AI 分析） | 增量，无上限 |
| `papers-historical.json` | 1960–2019 历史论文 | 增量 |
| `timeline.json` | 热力图计数 + AI 综述 | 增量（已有综述不重复调用） |
| `groups.json` | 课题组统计（合并历史+当前） | 每次全量重建 |
| `repos.json` | GitHub 仓库列表 | 增量 |
| `meta.json` | 最后更新时间 | 每次覆盖 |

---

## 5. 配置说明（config.py）

### 5.1 搜索关键词

```python
KEYWORDS = [
    "tip clearance",        # 短词优先，覆盖面广
    "casing treatment",
    "rotating stall",
    ...
]
```

**原则**：用短词广搜，靠 AI 评分（MIN_RELEVANCE=2）过滤不相关的。长词组（如 "circumferential distortion compressor"）容易漏论文。

### 5.2 目标期刊

```python
TARGET_JOURNALS = [
    {"name": "Journal of Turbomachinery",      "issn": "0889-504X"},
    {"name": "J. Eng. Gas Turbines and Power", "issn": "0742-4795"},
    {"name": "Journal of Propulsion and Power", "issn": "0748-4658"},
    {"name": "AIAA Journal",                    "issn": "0001-1452"},
]

HISTORICAL_JOURNALS = [  # 仅历史抓取使用
    {"name": "J. Eng. for Power (JEGTP前身)",   "issn": "0022-0825"},
    {"name": "J. Basic Engineering",            "issn": "0021-9223"},
]
```

通过 ISSN 精确匹配，不会混入其他期刊。

### 5.3 课题组

```python
RESEARCH_GROUPS = [
    {
        "name": "MIT GTL",
        "institution": "MIT",
        "pis": ["Greitzer", "Spakovszky", "C. S. Tan", "Choon Tan", "Paduano"],
    },
    ...
]
```

PI 姓名用子串匹配（`pi in author.lower()`），所以 "Greitzer" 能匹配 "E. M. Greitzer"。注意避免过短的名字（如 "He" 会误匹配 "Shepherd"）。

### 5.4 热力图话题

定义在 `scripts/fetch_papers_historical.py` 的 `DEFAULT_TOPICS`，也同步在 `index.html` 的 `DEFAULT_TOPICS`。当前 10 个话题：

1. 叶尖间隙
2. 机匣处理
3. 压缩机稳定性
4. 稳定性建模
5. 进气畸变
6. 跨音速/激波
7. 叶片气动设计
8. 离心压气机
9. 非定常流动
10. 气弹/振动

### 5.5 其他参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `FETCH_FROM_YEAR` | 2020 | 当前论文抓取起始年 |
| `FETCH_FROM_YEAR_HISTORICAL` | 1960 | 历史论文抓取起始年 |
| `MAX_PAPERS_PER_QUERY` | 50 | 每个关键词×期刊最多抓取篇数 |
| `MIN_RELEVANCE` | 2 | AI 评分低于此值的论文被过滤 |

---

## 6. 前端功能

### 6.1 PAPERS 标签页

- 显示所有论文（当前 + 历史），按日期倒序
- 支持搜索（标题/摘要/作者）
- 排序：入库日期 / 发表日期 / 相关度
- 按话题标签、课题组、已读状态筛选
- 每篇论文卡片显示：标题、作者、日期、期刊、AI 综述、创新点、结论等
- 可写评价（存 localStorage），影响后续 AI 评分

### 6.2 GROUPS 标签页

- 23 个课题组卡片，显示机构、PI 姓名、论文数、平均相关度
- 点击卡片筛选该组论文
- 支持在线编辑课题组信息

### 6.3 TIMELINE 标签页

- 左右分栏布局（60/40）
- 左侧：热力图，10 话题 × 14 个 5 年期间（1960–2029）
- 右侧：点击格子后显示 AI 综述 + 论文列表
- 期刊风格绿色渐变色阶，全局统一缩放
- 双行表头：年代（1960s, 1970s...）+ 5 年细分（60-64, 65-69...）

### 6.4 AI CHAT 标签页

- 基于论文库的问答，先检索相关论文再调 DeepSeek
- 流式输出，支持 Markdown 渲染
- API Key 存在浏览器 localStorage

### 6.5 其他

- **REPOS**：GitHub 相关仓库列表
- **BUILD**：项目开发时间线和技术栈说明
- **MANUAL**：内嵌使用手册
- **Wishlist**：右下角悬浮按钮，记录想查找的文献

---

## 7. GitHub Actions 自动更新

### 7.1 配置文件

`.github/workflows/pipeline.yml`：
- 每周一 UTC 02:00 自动运行
- 支持手动触发（Actions → Run workflow）
- 自动提交更新的数据文件

### 7.2 触发方式

1. **自动**：cron 定时
2. **手动**：GitHub → Actions → Run workflow
3. **本地**：`cd scripts && python run_pipeline.py`

### 7.3 注意事项

- GitHub Actions 的 `DEEPSEEK_API_KEY` 需在 Secrets 中配置
- 运行时间取决于新增论文数量（AI 分析是主要耗时）
- 历史论文首次抓取较慢（1960–2019，全量），后续增量很快

---

## 8. 本地开发

### 8.1 启动本地服务器

```bash
cd research-radar
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

### 8.2 修改后测试

前端修改：直接刷新浏览器即可。

后端修改：重新运行 `python run_pipeline.py`，然后刷新浏览器。

### 8.3 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 流水线报 401 | DeepSeek API Key 无效或过期 | 更新 `.env` 中的 key |
| 热力图数据为空 | `timeline.json` 不存在 | 运行完整流水线 |
| 课题组论文数偏少 | 只统计了 papers.json | 已修复，现在合并历史论文统计 |
| AI 对话报 401 | 浏览器 localStorage 中的旧 key | 清除后重新输入 |
| 论文搜不到某作者 | 关键词未覆盖或期刊不在列表中 | 在 config.py 中添加 |

---

## 9. 数据统计（v1.2）

| 指标 | 数量 |
|------|------|
| 当前论文（2020–今） | ~500 篇 |
| 历史论文（1960–2019） | ~2335 篇 |
| 总计 | ~2835 篇 |
| 监控期刊 | 4 + 2 历史 |
| 搜索关键词 | 17 |
| 研究话题 | 10 |
| 课题组 | 23 |
| AI 综述 | 130+ |

---

## 10. 更新日志

### v1.2（2026-03-31）
- 热力图重设计：5 年间隔，左右分栏，绿色渐变色阶
- 课题组合并：55 → 23 个，按实际实验室归属
- 关键词重构：短词优先，2835 篇论文
- 1960s 覆盖：新增 2 本历史期刊
- AI 对话 Markdown 渲染
- 代码审查：修复 XSS、去重、导入顺序等

### v1.1（2026-03-30）
- 时间轴热力图、文献愿望清单
- 历史论文抓取和时间线脚本

### v1.0（2026-03-28）
- 初始发布：论文抓取、AI 分析、课题组、标注、AI 问答
