# Research Radar — 项目说明

## 结构
- scripts/config.py          ← 关键词、分类标签、课题组，改这里
- scripts/run_pipeline.py    ← 主入口（抓取 → AI 分析 → 写入）
- scripts/fetch_papers.py    ← OpenAlex 抓取（并发，8线程）
- scripts/process_with_ai.py ← DeepSeek 分析（并发，5线程）
- scripts/fetch_repos.py     ← GitHub 仓库抓取
- scripts/server.py          ← Flask 服务（静态 + API + 流水线触发 + AI 对话）
- scripts/backfill_authors.py ← 一次性工具，已跑完，补全历史论文作者列表
- data/papers.json           ← 论文库（自动生成，勿手动编辑）
- data/repos.json            ← 仓库库
- data/annotations.json      ← 用户标注（写评价 + 已读状态）
- data/custom_groups.json    ← 用户自定义/编辑的课题组
- data/groups.json           ← 课题组统计（自动生成）
- index.html                 ← 前端（纯 HTML/CSS/JS，无构建工具）

## 常用命令
```bash
cd scripts && python server.py         # 启动本地服务（推荐，含 AI 对话）
cd scripts && python run_pipeline.py   # 直接跑完整流水线（不启动服务）
python fetch_papers.py                 # 只测试抓取
python process_with_ai.py             # 只测试 AI 处理
```

## 环境变量（本地 .env，不要提交）
```
DEEPSEEK_API_KEY=sk-xxx
GITHUB_TOKEN=ghp_xxx
```

## 当前配置（config.py）
- 关键词：19 个（覆盖叶尖间隙、机匣处理、稳定性分析/建模、进气畸变、激盘/体力模型）
- 目标期刊：4 本（J. Turbomachinery、J. Eng. Gas Turbines Power、J. Propulsion Power、AIAA J.）
- FETCH_FROM_YEAR = 2020
- MAX_PAPERS_PER_QUERY = 50（每个关键词每本期刊）
- MIN_RELEVANCE = 2（低于此分数过滤）

## 注意
- DeepSeek 用 deepseek-chat 模型，base_url = https://api.deepseek.com
- 抓取和 AI 处理都已并发，流水线总时间比原版快约 5-8 倍
- papers.json 最多保留 500 篇，按日期倒序
- custom_groups.json 存用户在网页端编辑的课题组，replaces 字段指向被替换的 ★ 作者名
- AI 对话端点：POST /api/chat，SSE 流式返回，先检索本地论文库再调 DeepSeek

## API 端点（server.py）
| 路径 | 方法 | 说明 |
|------|------|------|
| /api/annotate | POST | 写评价 / 标记已读 |
| /api/annotations | GET | 读取所有标注 |
| /api/groups/save | POST | 新增/更新自定义课题组 |
| /api/groups/delete | POST | 删除自定义课题组 |
| /api/groups/custom | GET | 读取自定义课题组 |
| /api/pipeline/run | POST | 触发后台流水线 |
| /api/pipeline/status | GET | 查询流水线状态和日志 |
| /api/chat | POST | AI 对话（SSE 流式） |

**跟 Claude Code 说话的实际方式**

在开始每个新功能或 bug fix 之前，先用 Plan Mode 让 Claude 生成计划再执行。  具体到这个项目，你可以这样说：
```
# 让它先规划再动手（适合新功能）
"在 fetch_papers.py 里加一个对 AIAA 官方 RSS 的抓取，
先给我看方案，不要直接改代码"

# 小修改直接说
"config.py 里加 3 个关键词：tip timing measurement、
labyrinth seal、rotor tip vortex"

# 调试
"跑 python run_pipeline.py 报错了，日志如下：[粘贴]，帮我修"

# 重构
"process_with_ai.py 的 process_one 函数太长，
帮我拆成独立的 build_prompt / call_api / validate_result 三个函数"
```

**上下文管理的关键**：会话结束时任何有价值的东西都应该写回磁盘（比如 CLAUDE.md 或日志），因为对话上下文是临时的，压缩后细节会丢失。  所以每次跑完如果有配置调整，让 Claude Code 直接帮你更新 `CLAUDE.md` 和 `config.py`。

---

## 二、API 方面需要做什么

三个 API，操作方式各不相同：

**1. DeepSeek API（必须）**

进 [platform.deepseek.com](https://platform.deepseek.com) → API Keys → 创建一个 key，充值按需（几十块够用很久）。

本地测试时在项目根放一个 `.env` 文件（记得加进 `.gitignore`）：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx