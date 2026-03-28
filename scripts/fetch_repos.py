"""
fetch_repos.py
通过 GitHub GraphQL API 搜索相关开源仓库，调用 DeepSeek 生成中文描述。
"""

import os
import json
import time
import logging
import hashlib
import requests
from openai import OpenAI
from config import GITHUB_KEYWORDS, MAX_REPOS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

GITHUB_GRAPHQL = "https://api.github.com/graphql"

# ─────────────────────────────────────────────
#  GitHub 抓取
# ─────────────────────────────────────────────

GQL_QUERY = """
query($query: String!, $first: Int!) {
  search(query: $query, type: REPOSITORY, first: $first) {
    nodes {
      ... on Repository {
        nameWithOwner
        description
        url
        stargazerCount
        updatedAt
        primaryLanguage { name }
        repositoryTopics(first: 5) {
          nodes { topic { name } }
        }
        object(expression: "HEAD:README.md") {
          ... on Blob { text }
        }
      }
    }
  }
}
"""

def repo_id(name: str) -> str:
    return hashlib.md5(name.lower().encode()).hexdigest()[:12]


def fetch_repos_for_keyword(
    keyword: str,
    github_token: str,
    count: int = 10,
) -> list[dict]:
    query_str = f"{keyword} stars:>50 sort:updated"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": GQL_QUERY,
        "variables": {"query": query_str, "first": count},
    }

    try:
        resp = requests.post(GITHUB_GRAPHQL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning(f"GitHub 请求失败 [{keyword}]: {e}")
        return []

    repos = []
    for node in data.get("data", {}).get("search", {}).get("nodes", []):
        if not node:
            continue
        name    = node.get("nameWithOwner", "")
        desc    = node.get("description") or ""
        url_    = node.get("url", "")
        stars   = node.get("stargazerCount", 0)
        updated = (node.get("updatedAt") or "")[:10]
        lang    = (node.get("primaryLanguage") or {}).get("name", "")
        topics  = [
            t["topic"]["name"]
            for t in (node.get("repositoryTopics") or {}).get("nodes", [])
        ]
        # README 前 1500 字，避免超 token
        readme  = (node.get("object") or {}).get("text") or ""
        readme  = readme[:1500].strip()

        repos.append({
            "id":          repo_id(name),
            "name":        name,
            "description": desc,
            "url":         url_,
            "stars":       stars,
            "updated":     updated,
            "language":    lang,
            "topics":      topics,
            "readme_excerpt": readme,
        })

    log.info(f"GitHub [{keyword}] → {len(repos)} 个仓库")
    return repos


def fetch_all_repos(github_token: str) -> list[dict]:
    seen: dict[str, dict] = {}
    for kw in GITHUB_KEYWORDS:
        for r in fetch_repos_for_keyword(kw, github_token, count=MAX_REPOS):
            seen[r["id"]] = r
        time.sleep(1)
    return list(seen.values())


# ─────────────────────────────────────────────
#  DeepSeek 处理
# ─────────────────────────────────────────────

REPO_SYSTEM = """你是一个航空发动机/流体力学/CFD 领域的技术助手。
只输出 JSON，不要任何其他文字。"""

REPO_USER = """请对以下 GitHub 仓库做简短的中文介绍：

仓库：{name}
描述：{description}
README（节选）：{readme}

返回 JSON：
{{
  "summary_zh": "50~80字，说明这个仓库做什么、适合什么场景",
  "tags_zh": ["标签1", "标签2"],
  "relevance": 2
}}
relevance：0=无关, 1=工具类/边缘相关, 2=有参考价值, 3=高度相关"""


def enrich_repos(
    repos: list[dict],
    existing_ids: set[str],
    delay: float = 0.5,
) -> list[dict]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("请设置环境变量 DEEPSEEK_API_KEY")

    client  = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    results = []

    for i, repo in enumerate(repos):
        if repo["id"] in existing_ids:
            continue

        log.info(f"[{i+1}/{len(repos)}] 处理仓库：{repo['name']}")
        prompt = REPO_USER.format(
            name=repo["name"],
            description=repo["description"],
            readme=repo["readme_excerpt"],
        )

        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": REPO_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200,
            )
            ai = json.loads(resp.choices[0].message.content)
            enriched = {**repo, **ai}
            enriched.pop("readme_excerpt", None)   # README 原文不写入最终 JSON
            results.append(enriched)
            log.info(f"  → 相关度 {ai.get('relevance')}，标签：{ai.get('tags_zh')}")
        except Exception as e:
            log.warning(f"  处理失败：{e}，使用原始描述")
            repo.pop("readme_excerpt", None)
            repo["summary_zh"] = repo["description"]
            repo["tags_zh"]    = []
            repo["relevance"]  = 1
            results.append(repo)

        time.sleep(delay)

    return results


# ─────────────────────────────────────────────
#  主入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN", "")
    repos = fetch_all_repos(token)
    enriched = enrich_repos(repos, existing_ids=set())
    print(json.dumps(enriched[:2], ensure_ascii=False, indent=2))
