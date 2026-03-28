# 设计文档：Research Radar 静态化迁移至 GitHub Pages

**日期：** 2026-03-28
**状态：** 已批准

---

## 目标

将当前依赖 Python Flask 服务器运行的文献检索网站，迁移为托管在 GitHub Pages（私有仓库）上的纯静态网站，同时保留全部功能：论文浏览/搜索、标注/已读、自定义课题组、AI 对话、流水线触发。

---

## 整体架构

```
GitHub 私有仓库
├── index.html                        ← 前端（改造后直接 fetch 静态文件）
├── data/
│   ├── papers.json                   ← 静态数据，由 GitHub Actions 定期更新
│   └── repos.json
├── scripts/                          ← Pipeline 脚本（仅在 GitHub Actions 中运行）
│   ├── config.py
│   ├── fetch_papers.py
│   ├── process_with_ai.py
│   ├── fetch_repos.py
│   └── run_pipeline.py
└── .github/workflows/
    └── pipeline.yml                  ← 定时 + 手动触发的 Actions workflow
```

`scripts/server.py` 整个删除，不再需要。

---

## 各功能改造方案

### 1. 论文数据加载

**现在：** 前端调 Flask `/api/papers`
**改后：** 直接 fetch 静态文件

```js
const papers = await fetch('./data/papers.json').then(r => r.json())
```

### 2. 标注 & 已读状态

**现在：** `POST /api/annotate`、`GET /api/annotations`
**改后：** 读写 `localStorage`，key 为 `rr_annotations`，JSON 结构与现有 `annotations.json` 保持一致。

### 3. 自定义课题组

**现在：** `/api/groups/save`、`/api/groups/delete`、`/api/groups/custom`
**改后：** 读写 `localStorage`，key 为 `rr_custom_groups`，JSON 结构与现有 `custom_groups.json` 保持一致。

### 4. AI 对话

**现在：** `POST /api/chat`（Flask 中转，SSE 流式）
**改后：** 前端直接调 DeepSeek API

- 端点：`https://api.deepseek.com/chat/completions`（SSE 流式保持不变）
- DeepSeek API Key：首次使用时弹出输入框，用户填入后存 `localStorage`（key: `rr_deepseek_key`）
- 论文检索逻辑：从已加载的 `papers` 数组中本地检索，不再依赖服务器

### 5. 流水线触发

**现在：** `POST /api/pipeline/run`（Flask 启动子进程）
**改后：** 前端调 GitHub Actions API

- 触发：`POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/pipeline.yml/dispatches`
- GitHub Personal Access Token：首次使用时弹出输入框，存 `localStorage`（key: `rr_github_token`）；Token 需要 `workflow` 权限（Fine-grained token → Actions: Read and write）
- 仓库信息（owner/repo）：硬编码在 `index.html` 顶部的配置对象中
- 进度查询：轮询 `GET /repos/{owner}/{repo}/actions/runs`，展示最新 run 的状态

### 6. GitHub Actions Workflow（新增）

文件：`.github/workflows/pipeline.yml`

```yaml
on:
  schedule:
    - cron: '0 2 * * 1'   # 每周一 UTC 02:00 自动运行
  workflow_dispatch:        # 支持手动触发 / API 触发

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r scripts/requirements.txt
      - run: cd scripts && python run_pipeline.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "auto: update papers.json"
          file_pattern: data/papers.json data/repos.json data/groups.json
```

Secrets 需要在 GitHub 仓库设置中配置：`DEEPSEEK_API_KEY`。

---

## GitHub Pages 配置

- 仓库设为**公开（public）**，在 Settings → Pages 中，Source 选 `main` 分支，根目录 `/`
- 访问地址：`https://{username}.github.io/{repo}/`
- **安全说明：** DeepSeek API Key 和 GitHub Token 均为运行时由用户填入并存 localStorage，不写入任何代码文件，公开仓库不会泄露。

---

## 不改变的部分

- `index.html` 的整体 UI、样式、搜索/过滤逻辑
- `scripts/` 下所有 Python 脚本的逻辑
- `data/papers.json` 的数据结构
- `config.py` 的配置方式

---

## 改动范围总结

| 文件 | 操作 |
|------|------|
| `index.html` | 修改：替换所有 API 调用为静态 fetch / localStorage / 直接调外部 API |
| `scripts/server.py` | 删除 |
| `.github/workflows/pipeline.yml` | 新增 |
| `data/*.json` | 不变（作为静态资源提供） |
| `scripts/*.py` | 不变（仅在 Actions 中运行） |
