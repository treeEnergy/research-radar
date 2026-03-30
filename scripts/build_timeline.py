# -*- coding: utf-8 -*-
"""
build_timeline.py
Generate data/timeline.json: count papers by topic x 5-year period, generate DeepSeek summaries.
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

PERIODS = list(range(1970, 2030, 5))  # [1970, 1975, 1980, ..., 2025]


def get_period(year: int) -> int:
    """Map a year to its 5-year period start: 2023 → 2020, 1987 → 1985."""
    return (year // 5) * 5


def group_papers_by_topic_period(
    papers: list[dict], topics: list[dict]
) -> dict[str, dict[int, list[str]]]:
    """
    Returns {topic_label: {period: [paper_id, ...]}} for non-empty cells.
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
        period = get_period(year)
        if period not in PERIODS:
            continue

        paper_id = paper.get("id", "")
        if not paper_id:
            continue

        if "topics_matched" in paper:
            matched_labels = set(paper["topics_matched"])
        else:
            matched_labels = set(compute_topics_matched(paper, topics))

        for label in matched_labels:
            if label not in result:
                continue
            if period not in result[label]:
                result[label][period] = []
            if paper_id not in result[label][period]:
                result[label][period].append(paper_id)

    return {label: periods for label, periods in result.items() if periods}


def _get_deepseek_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("请设置环境变量 DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def _generate_summary(client: OpenAI, topic_label: str, period: int,
                      titles: list[str]) -> str:
    """Call DeepSeek to generate a period summary."""
    titles_text = "\n".join(f"- {t}" for t in titles[:30])  # max 30 titles
    period_end = period + 4
    prompt = (
        f'以下是{period}-{period_end}年关于"{topic_label}"的{len(titles)}篇论文标题：\n\n'
        f"{titles_text}\n\n"
        "请用2-4句话（中文）概括这个时期该领域的主要研究进展和贡献。"
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
        log.warning(f"DeepSeek summary failed [{topic_label} {period}-{period+4}]: {e}")
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

    # 3. Group by topic x 5-year period
    paper_map = {p["id"]: p for p in all_papers}
    grouped = group_papers_by_topic_period(all_papers, topics)

    # 4. Load existing timeline.json for incremental summaries
    existing: dict = {}
    if OUTPUT_PATH.exists():
        try:
            existing_data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            for t in existing_data.get("topics", []):
                for period_str, cell in t.get("periods", t.get("decades", {})).items():
                    key = f"{t['label']}__{period_str}"
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
        periods_data = grouped.get(label, {})
        periods_out = {}

        for period in PERIODS:
            ids = periods_data.get(period, [])
            if not ids:
                continue

            cache_key = f"{label}__{period}"
            summary = existing.get(cache_key, "")

            if not summary:
                titles = [paper_map[pid]["title"] for pid in ids if pid in paper_map]
                if titles:
                    if client is None:
                        client = _get_deepseek_client()
                    log.info(f"生成摘要：{label} {period}-{period+4}（{len(titles)} 篇）")
                    summary = _generate_summary(client, label, period, titles)
                    new_summaries += 1

            periods_out[str(period)] = {
                "count": len(ids),
                "paper_ids": ids,
                "summary": summary,
            }

        if periods_out:
            topics_output.append({"label": label, "periods": periods_out})

    log.info(f"新生成摘要：{new_summaries} 个")

    # 6. Write timeline.json
    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "periods": PERIODS,
        "topics": topics_output,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"timeline.json 已写入：{len(topics_output)} 个话题 → {OUTPUT_PATH}")


if __name__ == "__main__":
    build_timeline()
