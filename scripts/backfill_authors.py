"""
backfill_authors.py
从 OpenAlex 重新抓取所有现有论文的完整作者列表，修复之前被截断到 4 人的问题。
"""

import json
import time
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
OPENALEX_API = "https://api.openalex.org/works"
POLITE_EMAIL = "research@example.com"


def fetch_authors_by_doi(doi: str) -> list[str] | None:
    """通过 DOI 查询 OpenAlex，返回完整作者列表；失败返回 None"""
    clean_doi = doi.replace("https://doi.org/", "").strip()
    if not clean_doi:
        return None
    try:
        resp = requests.get(
            f"{OPENALEX_API}/https://doi.org/{clean_doi}",
            params={"select": "authorships", "mailto": POLITE_EMAIL},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        authors = [
            a["author"]["display_name"]
            for a in data.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        return authors if authors else None
    except Exception as e:
        log.warning(f"DOI 查询失败 {clean_doi}: {e}")
        return None


def main():
    papers_path = DATA_DIR / "papers.json"
    papers = json.loads(papers_path.read_text(encoding="utf-8"))
    log.info(f"共 {len(papers)} 篇论文，开始补全作者列表…")

    updated = 0
    failed = 0

    for i, paper in enumerate(papers):
        doi_url = paper.get("url", "")
        if not doi_url:
            log.warning(f"[{i+1}/{len(papers)}] 无 DOI，跳过：{paper['title'][:50]}")
            failed += 1
            continue

        authors = fetch_authors_by_doi(doi_url)
        if authors is None:
            log.warning(f"[{i+1}/{len(papers)}] 查询失败：{paper['title'][:50]}")
            failed += 1
        elif len(authors) > len(paper.get("authors", [])):
            old_count = len(paper.get("authors", []))
            paper["authors"] = authors
            updated += 1
            log.info(f"[{i+1}/{len(papers)}] {old_count}→{len(authors)} 位作者：{paper['title'][:50]}")
        else:
            log.info(f"[{i+1}/{len(papers)}] 无变化（{len(paper.get('authors',[]))} 位）：{paper['title'][:40]}")

        time.sleep(0.2)  # 礼貌限速

    # 写回
    papers_path.write_text(
        json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"完成：更新 {updated} 篇，失败/无DOI {failed} 篇")


if __name__ == "__main__":
    main()
