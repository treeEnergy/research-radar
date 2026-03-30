"""
build_timeline.py
Generate data/timeline.json: count papers by topic x decade, generate DeepSeek summaries.
Incremental: skip cells that already have summaries.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI

from fetch_papers_historical import get_topics, compute_topics_matched

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_PATH = DATA_DIR / "papers-historical.json"
CURRENT_PATH = DATA_DIR / "papers.json"
OUTPUT_PATH = DATA_DIR / "timeline.json"

DECADES = [1970, 1980, 1990, 2000, 2010, 2020]


def get_decade(year: int) -> int:
    return (year // 10) * 10


def group_papers_by_topic_decade(
    papers: list[dict], topics: list[dict]
) -> dict[str, dict[int, list[str]]]:
    """
    Returns {topic_label: {decade: [paper_id, ...]}} for non-empty cells.
    A paper is included in a topic if its topics_matched OR tags contains the label.
    """
    result: dict[str, dict[int, list[str]]] = {}
    for topic in topics:
        label = topic["label"]
        result[label] = {}

    for paper in papers:
        year = paper.get("year")
        if not year:
            continue
        decade = get_decade(year)
        if decade not in DECADES:
            continue

        paper_id = paper.get("id", "")
        if not paper_id:
            continue

        # Use topics_matched if present (historical); otherwise compute from text (current papers)
        if "topics_matched" in paper:
            matched_labels = set(paper["topics_matched"])
        else:
            matched_labels = set(compute_topics_matched(paper, topics))

        for label in matched_labels:
            if label not in result:
                continue
            if decade not in result[label]:
                result[label][decade] = []
            if paper_id not in result[label][decade]:
                result[label][decade].append(paper_id)

    # Remove topics with no data at all
    return {label: decades for label, decades in result.items() if decades}


def _get_deepseek_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("请设置环境变量 DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def _generate_summary(client: OpenAI, topic_label: str, decade: int,
                      titles: list[str]) -> str:
    """Call DeepSeek to generate a decade summary; return empty string on failure."""
    titles_text = "\n".join(f"- {t}" for t in titles[:30])  # max 30 titles
    prompt = (
        f"以下是{decade}年代关于“{topic_label}”的{len(titles)}篇论文标题：\n\n"
        f"{titles_text}\n\n"
        "请用3-5句话（中文）概括这个年代该领域的主要研究进展和贡献。"
        "要求：具体提及关键工作或发现，避免泛泛而谈。"
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"DeepSeek summary failed [{topic_label} {decade}s]: {e}")
        return ""


def build_timeline() -> None:
    """Main function: generate/update data/timeline.json."""
    # 1. Load papers
    historical: list[dict] = []
    if HISTORICAL_PATH.exists():
        historical = json.loads(HISTORICAL_PATH.read_text(encoding="utf-8"))
    current: list[dict] = []
    if CURRENT_PATH.exists():
        current = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))

    all_papers = historical + current
    log.info(f"加载论文：历史 {len(historical)} 篇 + 当前 {len(current)} 篇 = {len(all_papers)} 篇")

    # 2. Load topic list
    topics = get_topics()
    log.info(f"话题列表：{[t['label'] for t in topics]}")

    # 3. Group by topic x decade
    paper_map = {p["id"]: p for p in all_papers}
    grouped = group_papers_by_topic_decade(all_papers, topics)

    # 4. Load existing timeline.json for incremental summaries
    existing: dict = {}
    if OUTPUT_PATH.exists():
        try:
            existing_data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            for t in existing_data.get("topics", []):
                for decade_str, cell in t.get("decades", {}).items():
                    key = f"{t['label']}__{decade_str}"
                    if cell.get("summary"):
                        existing[key] = cell["summary"]
        except Exception as e:
            log.warning(f"读取现有 timeline.json 失败（将全量重建）：{e}")

    # 5. Generate summaries (skip cells with existing summaries)
    client = None
    new_summaries = 0

    topics_output = []
    for topic in topics:
        label = topic["label"]
        decades_data = grouped.get(label, {})
        decades_out = {}

        for decade in DECADES:
            ids = decades_data.get(decade, [])
            if not ids:
                continue

            cache_key = f"{label}__{decade}"
            summary = existing.get(cache_key, "")

            if not summary:
                titles = [paper_map[pid]["title"] for pid in ids if pid in paper_map]
                if titles:
                    if client is None:
                        client = _get_deepseek_client()
                    log.info(f"生成摘要：{label} {decade}s（{len(titles)} 篇）")
                    summary = _generate_summary(client, label, decade, titles)
                    new_summaries += 1

            decades_out[str(decade)] = {
                "count": len(ids),
                "paper_ids": ids,
                "summary": summary,
            }

        if decades_out:
            topics_output.append({"label": label, "decades": decades_out})

    log.info(f"新生成摘要：{new_summaries} 个")

    # 6. Write timeline.json
    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decades": DECADES,
        "topics": topics_output,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"timeline.json 已写入：{len(topics_output)} 个话题 → {OUTPUT_PATH}")


if __name__ == "__main__":
    build_timeline()
