"""
run_pipeline.py
主流水线：抓取 → AI 处理 → 写入 JSON
在本地或 GitHub Actions 中直接运行。
"""

import os
import json
import logging
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
from datetime import datetime, timezone
from pathlib import Path

from fetch_papers import fetch_all_papers
from process_with_ai import process_papers
from fetch_repos import fetch_all_repos, enrich_repos
from fetch_papers_historical import fetch_papers_historical_incremental
from build_timeline import build_timeline
from config import RESEARCH_GROUPS

def load_all_groups() -> list:
    """合并 config.py 预设组 + data/custom_groups.json 自定义组"""
    custom_path = DATA_DIR / "custom_groups.json"
    custom = []
    if custom_path.exists():
        import json as _json
        custom = _json.loads(custom_path.read_text(encoding="utf-8"))
    return RESEARCH_GROUPS + custom

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# 输出目录（相对于项目根）
DATA_DIR = Path(__file__).parent.parent / "data"


# ─────────────────────────────────────────────
#  JSON 读写工具
# ─────────────────────────────────────────────

def load_json(path: Path) -> list[dict]:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"已写入 {path}（{len(data)} 条）")


# ─────────────────────────────────────────────
#  论文流水线
# ─────────────────────────────────────────────

def run_papers_pipeline() -> None:
    papers_path = DATA_DIR / "papers.json"
    existing    = load_json(papers_path)
    existing_ids = {p["id"] for p in existing}

    log.info(f"现有论文库：{len(existing)} 篇，开始增量更新")

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

    # 2. DeepSeek 处理（跳过已存在 id）
    new_papers = process_papers(raw, existing_ids=existing_ids)

    if not new_papers:
        log.info("没有新论文入库")
        return

    # 3. 合并，按日期倒序，只保留最新 500 篇
    combined = new_papers + existing
    combined.sort(key=lambda p: p.get("date", ""), reverse=True)
    combined = combined[:500]

    # 4. 新论文打入库时间戳
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_ids = {p["id"] for p in new_papers}
    for p in combined:
        if p["id"] in new_ids and not p.get("fetched_at"):
            p["fetched_at"] = today

    # 5. 课题组匹配 + 高频作者统计
    tag_groups(combined)
    save_json(papers_path, combined)
    build_groups_json(combined)


# ─────────────────────────────────────────────
#  课题组匹配
# ─────────────────────────────────────────────

def tag_groups(papers: list[dict]) -> None:
    """给每篇论文打上所属课题组标签"""
    all_groups = load_all_groups()
    for paper in papers:
        authors = paper.get("authors", [])
        matched = []
        for group in all_groups:
            for pi in group["pis"]:
                pi_lower = pi.lower()
                if any(pi_lower in a.lower() for a in authors):
                    matched.append(group["name"])
                    break
        paper["groups"] = matched


def build_groups_json(papers: list[dict]) -> None:
    """统计各课题组论文数量和平均相关度，写入 groups.json
    合并 papers.json + papers-historical.json 做统计。
    """
    # 加载历史论文并合并（去重）
    hist_path = DATA_DIR / "papers-historical.json"
    historical: list[dict] = []
    if hist_path.exists():
        historical = json.loads(hist_path.read_text(encoding="utf-8"))
    existing_ids = {p["id"] for p in papers}
    all_papers = papers + [p for p in historical if p["id"] not in existing_ids]

    # 给历史论文也打课题组标签
    tag_groups(all_papers)

    # 预设课题组统计
    all_groups = load_all_groups()
    stats: dict[str, dict] = {
        g["name"]: {
            "name": g["name"],
            "institution": g["institution"],
            "paper_ids": [],
            "total": 0,
            "avg_relevance": 0.0,
            "preset": True,
            "custom": g.get("custom", False),
        }
        for g in all_groups
    }

    # 统计高频作者（出现 5 篇以上视为值得追踪）
    from collections import Counter
    author_counter: Counter = Counter()
    paper_by_author: dict[str, list[str]] = {}
    for p in all_papers:
        for a in p.get("authors", []):
            author_counter[a] += 1
            paper_by_author.setdefault(a, []).append(p["id"])

    # 匹配论文到预设课题组
    for p in all_papers:
        for g_name in p.get("groups", []):
            if g_name in stats:
                stats[g_name]["paper_ids"].append(p["id"])

    # 计算平均相关度
    paper_map = {p["id"]: p for p in all_papers}
    for g in stats.values():
        ids = g["paper_ids"]
        g["total"] = len(ids)
        if ids:
            rels = [paper_map[i].get("relevance", 0) for i in ids if i in paper_map]
            rels = [r for r in rels if r]  # 历史论文无 relevance，跳过
            g["avg_relevance"] = round(sum(rels) / len(rels), 1) if rels else 0.0
        del g["paper_ids"]

    # 高频作者补充（不在预设组中）
    preset_pis = {pi.lower() for g in all_groups for pi in g["pis"]}
    for author, count in author_counter.most_common(50):
        if count < 5:
            break
        if any(author.lower() in pi for pi in preset_pis):
            continue
        ids = paper_by_author[author]
        rels = [paper_map[i].get("relevance", 0) for i in ids if i in paper_map]
        rels = [r for r in rels if r]
        stats[f"★ {author}"] = {
            "name": f"★ {author}",
            "institution": "（自动识别）",
            "total": count,
            "avg_relevance": round(sum(rels) / len(rels), 1) if rels else 0.0,
            "preset": False,
        }

    result = sorted(stats.values(), key=lambda x: (-x["total"], -x["avg_relevance"]))
    save_json(DATA_DIR / "groups.json", result)


# ─────────────────────────────────────────────
#  GitHub 仓库流水线
# ─────────────────────────────────────────────

def run_repos_pipeline() -> None:
    repos_path   = DATA_DIR / "repos.json"
    existing     = load_json(repos_path)
    existing_ids = {r["id"] for r in existing}

    github_token = os.getenv("GITHUB_TOKEN", "")
    if not github_token:
        log.warning("GITHUB_TOKEN 未设置，跳过 GitHub 仓库抓取")
        return

    log.info(f"现有仓库库：{len(existing)} 个，开始增量更新")

    raw_repos  = fetch_all_repos(github_token)
    new_repos  = enrich_repos(raw_repos, existing_ids=existing_ids)

    if not new_repos:
        log.info("没有新仓库入库")
        return

    # 合并，按 stars 倒序，保留最新 200 个
    combined = new_repos + existing
    seen: dict[str, dict] = {}
    for r in combined:
        seen[r["id"]] = r
    combined = sorted(seen.values(), key=lambda r: r.get("stars", 0), reverse=True)
    combined = combined[:200]

    save_json(repos_path, combined)


# ─────────────────────────────────────────────
#  写入最后更新时间
# ─────────────────────────────────────────────

def write_meta() -> None:
    meta = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_json(DATA_DIR / "meta.json", [meta])


# ─────────────────────────────────────────────
#  主函数
# ─────────────────────────────────────────────

def main() -> None:
    log.info("════════ 研究雷达流水线启动 ════════")

    run_papers_pipeline()
    run_repos_pipeline()
    write_meta()

    # 6. 历史论文增量抓取
    log.info("─── 历史论文增量抓取 ───")
    fetch_papers_historical_incremental()

    # 7. 生成时间轴数据
    log.info("─── 生成时间轴数据 ───")
    build_timeline()

    log.info("════════ 流水线完成 ════════")


if __name__ == "__main__":
    main()
