# Research Radar 🔭

**为特定研究方向定制的文献追踪网站** — 自动从期刊抓取论文，AI 分析摘要，支持标注、课题组追踪和 AI 问答。

> 本项目由 [treeEnergy](https://github.com/treeEnergy) 创建，默认配置针对**压气机气动稳定性**方向（叶尖间隙、机匣处理、进气畸变、稳定性建模），**你可以改成任何研究方向**。

**演示：** https://treeEnergy.github.io/research-radar/

---

## 功能

- 🔍 **自动抓取**：从 OpenAlex 按关键词 + 期刊筛选论文
- 🤖 **AI 分析**：DeepSeek 自动生成中文综述、创新点、结论、相关度评分
- 💬 **AI 问答**：基于本地论文库的领域专属对话
- 📌 **标注系统**：标记已读、写评价笔记
- 👥 **课题组追踪**：按 PI 姓名追踪特定课题组的论文
- ⚡ **一键更新**：网页内触发 GitHub Actions 流水线，每周自动运行

---

## 部署你自己的版本（5 分钟）

### 前置条件

- GitHub 账号（免费）
- [DeepSeek API Key](https://platform.deepseek.com)（按量计费，几十元可用很久）

### 步骤

**1. Fork 本仓库**

点右上角 **Fork** → 仓库名建议保持 `research-radar`（也可以改）。

**2. 修改检索配置**

编辑 `scripts/config.py`，改成你自己的研究方向：

```python
# 改成你关心的关键词
KEYWORDS = [
    "your keyword 1",
    "your keyword 2",
    ...
]

# 改成你关心的期刊（填 ISSN）
TARGET_JOURNALS = [
    {"name": "Journal Name", "issn": "xxxx-xxxx"},
    ...
]

# 改成你关注的课题组
RESEARCH_GROUPS = [
    {"name": "Group Name", "institution": "University", "pis": ["Last Name"]},
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

打开网站，点右上角 **▶ 更新检索**：
- 首次会弹窗要求输入 **GitHub Token**（用于触发流水线）
- 去 [GitHub Token 设置页](https://github.com/settings/personal-access-tokens/new) 创建，选你的仓库，**Actions: Read and write** 权限

**6. 首次使用 AI 对话**

点右下角聊天图标，首次会弹窗要求输入 **DeepSeek API Key**（`sk-` 开头）。

---

## 技术架构

```
GitHub 仓库（静态资源）
├── index.html          ← 纯前端，无构建工具
├── data/papers.json    ← 论文库（GitHub Actions 自动更新）
└── scripts/            ← Python 抓取 + AI 分析脚本

运行时数据流：
浏览器 → fetch data/*.json       （静态论文数据）
浏览器 → DeepSeek API            （AI 对话，Key 存 localStorage）
浏览器 → GitHub Actions API      （触发流水线，Token 存 localStorage）
GitHub Actions → OpenAlex API   （抓取论文）
GitHub Actions → DeepSeek API   （AI 分析）
GitHub Actions → commit 回仓库  （更新 papers.json）
```

**所有敏感 Key 仅存在用户浏览器的 localStorage 中，不会上传到任何服务器。**

---

## 自定义

### 添加关键词
编辑 `scripts/config.py` 的 `KEYWORDS` 列表，推送后下次流水线自动生效。

### 调整 AI 分析的领域提示词
编辑 `scripts/process_with_ai.py` 中的 `SYSTEM_PROMPT`，改成你的研究方向描述。

### 调整 AI 对话的系统提示词
编辑 `index.html` 中 `sendChat()` 函数里的 `CHAT_SYSTEM` 字符串。

### 修改自动更新频率
编辑 `.github/workflows/pipeline.yml` 中的 `cron` 表达式，默认每周一 UTC 02:00。

---

## 数据说明

- `data/papers.json`：最多保留 500 篇，按日期倒序，由 GitHub Actions 自动维护
- `data/annotations.json`：**不再使用**（已迁移到 localStorage）
- 标注/已读状态存在浏览器本地，清除浏览器缓存会丢失

---

## License

MIT — 自由使用、修改、分发。
