# Timeline + Wishlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Timeline heatmap (topic × decade, 1970–present) with AI-generated era summaries and a Wishlist floating panel to Research Radar.

**Architecture:** Three new Python scripts handle data (historical paper fetch, timeline build, pipeline integration); `index.html` gets a new TIMELINE nav tab with heatmap UI + drill-down panel, plus an always-visible wishlist button. AI summaries are pre-generated during the pipeline run and cached in `data/timeline.json`; the wishlist uses `localStorage` only.

**Tech Stack:** Python 3.11, OpenAlex REST API, DeepSeek API (`openai` SDK), vanilla JS/HTML/CSS, GitHub Actions.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/config.py` | Modify | Add `FETCH_FROM_YEAR_HISTORICAL = 1970` |
| `scripts/fetch_papers_historical.py` | Create | Fetch 1970–2019 papers from OpenAlex, compute `topics_matched` |
| `scripts/build_timeline.py` | Create | Group papers by topic×decade, generate DeepSeek summaries, write `data/timeline.json` |
| `scripts/run_pipeline.py` | Modify | Add historical fetch + timeline build steps at end of `main()` |
| `.github/workflows/pipeline.yml` | Modify | Add `data/papers-historical.json` and `data/timeline.json` to auto-commit |
| `index.html` | Modify | TIMELINE tab, heatmap, drill-down panel, wishlist button + panel |

---

## Task 1: Add `FETCH_FROM_YEAR_HISTORICAL` to config.py

**Files:**
- Modify: `scripts/config.py` (after `FETCH_FROM_YEAR = 2020` line, around line 33)

- [ ] **Step 1: Add the constant**

Open `scripts/config.py`. Find the line `FETCH_FROM_YEAR = 2020`. Add the new constant immediately after:

```python
# 只抓近几年的论文
FETCH_FROM_YEAR = 2020

# 历史论文起始年份（fetch_papers_historical.py 使用）
FETCH_FROM_YEAR_HISTORICAL = 1970
```

- [ ] **Step 2: Verify**

```bash
cd scripts && python -c "from config import FETCH_FROM_YEAR_HISTORICAL; print(FETCH_FROM_YEAR_HISTORICAL)"
```

Expected output: `1970`

- [ ] **Step 3: Commit**

```bash
git add scripts/config.py
git commit -m "feat: add FETCH_FROM_YEAR_HISTORICAL = 1970 to config"
```

---

## Task 2: `scripts/fetch_papers_historical.py`

**Files:**
- Create: `scripts/fetch_papers_historical.py`
- Create: `scripts/tests/test_fetch_historical.py`
- Modify: `scripts/requirements.txt` (add `pytest`)

- [ ] **Step 1: Add pytest to requirements.txt**

Open `scripts/requirements.txt` and append:
```
pytest
```

- [ ] **Step 2: Create tests directory**

```bash
mkdir -p scripts/tests && touch scripts/tests/__init__.py
```

- [ ] **Step 3: Write the failing tests**

Create `scripts/tests/test_fetch_historical.py`:

```python
"""Tests for fetch_papers_historical utility functions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fetch_papers_historical import matches_topic, compute_topics_matched, reconstruct_abstract


def test_matches_topic_title():
    paper = {"title": "Casing Treatment Stall Margin Improvement", "abstract": "", "keywords": []}
    assert matches_topic(paper, ["casing treatment"]) is True


def test_matches_topic_abstract():
    paper = {"title": "Compressor study", "abstract": "tip clearance effect on stage efficiency", "keywords": []}
    assert matches_topic(paper, ["tip clearance effect"]) is True


def test_matches_topic_keywords():
    paper = {"title": "Axial compressor", "abstract": "stability analysis", "keywords": ["compressor surge"]}
    assert matches_topic(paper, ["compressor surge"]) is True


def test_matches_topic_case_insensitive():
    paper = {"title": "INLET DISTORTION COMPRESSOR STUDY", "abstract": "", "keywords": []}
    assert matches_topic(paper, ["inlet distortion compressor"]) is True


def test_matches_topic_no_match():
    paper = {"title": "Heat exchanger design", "abstract": "thermal hydraulics", "keywords": []}
    assert matches_topic(paper, ["tip clearance", "casing treatment"]) is False


def test_compute_topics_matched_single():
    paper = {"title": "Casing treatment stall margin", "abstract": "", "keywords": []}
    topics = [
        {"label": "机匣处理", "terms": ["casing treatment"]},
        {"label": "叶尖间隙", "terms": ["tip clearance"]},
    ]
    result = compute_topics_matched(paper, topics)
    assert result == ["机匣处理"]


def test_compute_topics_matched_multiple():
    paper = {"title": "tip clearance casing treatment effects", "abstract": "", "keywords": []}
    topics = [
        {"label": "机匣处理", "terms": ["casing treatment"]},
        {"label": "叶尖间隙", "terms": ["tip clearance"]},
    ]
    result = compute_topics_matched(paper, topics)
    assert set(result) == {"机匣处理", "叶尖间隙"}


def test_reconstruct_abstract_empty():
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""


def test_reconstruct_abstract():
    inv = {"Hello": [0], "world": [1]}
    result = reconstruct_abstract(inv)
    assert result == "Hello world"
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd scripts && python -m pytest tests/test_fetch_historical.py -v
```

Expected: `ImportError: No module named 'fetch_papers_historical'` (module doesn't exist yet)

- [ ] **Step 5: Create `scripts/fetch_papers_historical.py`**

```python
"""
fetch_papers_historical.py
从 OpenAlex 抓取 1970–2019 年历史论文，增量写入 data/papers-historical.json。
使用 OpenAlex 原生 W-ID（非 MD5 哈希），包含所有可用字段供将来扩展。
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from config import TARGET_JOURNALS, FETCH_FROM_YEAR, FETCH_FROM_YEAR_HISTORICAL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "papers-historical.json"
OPENALEX_API = "https://api.openalex.org/works"
POLITE_EMAIL = "research@example.com"

# 默认话题列表（与 index.html DEFAULT_TOPICS 保持一致）
# 当 data/topics.json 不存在时使用
DEFAULT_TOPICS = [
    {"label": "叶尖间隙", "terms": [
        "compressor tip clearance", "non-axisymmetric tip clearance", "tip clearance effect",
    ]},
    {"label": "机匣处理", "terms": [
        "casing treatment stall margin", "casing treatment",
    ]},
    {"label": "压缩机稳定性", "terms": [
        "axial compressor rotating stall", "compressor stability",
        "compressor surge", "stall inception compressor",
    ]},
    {"label": "稳定性建模", "terms": [
        "actuator disk model compressor", "actuator disk model fan",
        "compressor stability model", "three-dimensional stability model turbomachinery",
        "Moore Greitzer model compressor", "body force model compressor",
    ]},
    {"label": "进气畸变", "terms": [
        "inlet distortion compressor", "circumferential distortion compressor",
        "inlet distortion fan", "total pressure distortion turbomachinery",
    ]},
]


def get_topics() -> list[dict]:
    """读取 data/topics.json，若不存在则返回 DEFAULT_TOPICS。"""
    topics_path = DATA_DIR / "topics.json"
    if topics_path.exists():
        try:
            return json.loads(topics_path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"读取 topics.json 失败，使用默认话题列表：{e}")
    return DEFAULT_TOPICS


def reconstruct_abstract(inv: dict) -> str:
    """把 OpenAlex 倒排索引还原为摘要文本。"""
    if not inv:
        return ""
    pairs = [(pos, word) for word, positions in inv.items() for pos in positions]
    return " ".join(word for _, word in sorted(pairs))


def matches_topic(paper: dict, terms: list[str]) -> bool:
    """大小写不敏感，在 title/abstract/keywords 中匹配任一词。"""
    text_parts = [
        paper.get("title", ""),
        paper.get("abstract", ""),
        " ".join(paper.get("keywords", [])),
    ]
    combined = " ".join(text_parts).lower()
    return any(term.lower() in combined for term in terms)


def compute_topics_matched(paper: dict, topics: list[dict]) -> list[str]:
    """返回所有匹配该论文的话题 label 列表。"""
    return [t["label"] for t in topics if matches_topic(paper, t.get("terms", []))]


def _fetch_page(keyword: str, issn: str, journal_name: str,
                from_year: int, to_year: int, page: int) -> tuple[list[dict], bool]:
    """抓取一页 OpenAlex 结果，返回 (papers, has_more)。"""
    params = {
        "search": keyword,
        "filter": (
            f"primary_location.source.issn:{issn},"
            f"from_publication_date:{from_year}-01-01,"
            f"to_publication_date:{to_year}-12-31"
        ),
        "per-page": 200,
        "page": page,
        "sort": "publication_date:asc",
        "select": "id,title,abstract_inverted_index,authorships,publication_date,doi,"
                  "primary_location,keywords",
        "mailto": POLITE_EMAIL,
    }
    try:
        resp = requests.get(OPENALEX_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning(f"OpenAlex 历史抓取失败 [{journal_name} / {keyword} p{page}]: {e}")
        return [], False

    results = data.get("results", [])
    meta = data.get("meta", {})
    has_more = (page * 200) < meta.get("count", 0)

    papers = []
    for item in results:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        openalex_id = (item.get("id") or "").replace("https://openalex.org/", "")
        if not openalex_id:
            continue
        date = item.get("publication_date") or ""
        year = int(date[:4]) if date and len(date) >= 4 else None
        if not year:
            continue

        abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
        authors = [
            a["author"]["display_name"]
            for a in item.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        doi = item.get("doi") or ""
        url = doi if doi.startswith("https://doi.org/") else (
            f"https://doi.org/{doi}" if doi else ""
        )
        venue = (
            (item.get("primary_location") or {})
            .get("source", {}).get("display_name", "") or journal_name
        )
        kw_list = [
            kw.get("display_name", "")
            for kw in (item.get("keywords") or [])
            if kw.get("display_name")
        ]

        papers.append({
            "id": openalex_id,
            "title": title,
            "date": date,
            "year": year,
            "authors": authors,
            "venue": venue,
            "source": "OpenAlex",
            "url": url,
            "abstract": abstract,
            "keywords": kw_list,
            "topics_matched": [],  # populated after dedup
        })

    return papers, has_more


def _fetch_keyword(keyword: str, issn: str, journal_name: str,
                   from_year: int, to_year: int) -> list[dict]:
    """分页抓取某关键词+期刊的所有历史论文。"""
    all_papers: dict[str, dict] = {}
    page = 1
    while True:
        papers, has_more = _fetch_page(keyword, issn, journal_name, from_year, to_year, page)
        for p in papers:
            all_papers[p["id"]] = p
        if not has_more:
            break
        page += 1
        time.sleep(0.2)
    return list(all_papers.values())


def fetch_all_historical(from_year: int = FETCH_FROM_YEAR_HISTORICAL,
                         to_year: int = FETCH_FROM_YEAR - 1) -> list[dict]:
    """抓取全量历史论文并计算 topics_matched。"""
    from config import KEYWORDS
    tasks = [
        (kw, journal["issn"], journal["name"])
        for journal in TARGET_JOURNALS
        for kw in KEYWORDS
    ]
    log.info(f"历史论文抓取：{from_year}–{to_year}，{len(tasks)} 个查询（4 线程）")

    all_papers: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_keyword, kw, issn, name, from_year, to_year): (name, kw)
            for kw, issn, name in tasks
        }
        for future in as_completed(futures):
            for p in future.result():
                all_papers[p["id"]] = p

    result = list(all_papers.values())
    log.info(f"历史论文去重后：{len(result)} 篇，计算 topics_matched…")

    topics = get_topics()
    for p in result:
        p["topics_matched"] = compute_topics_matched(p, topics)

    result.sort(key=lambda p: p.get("date", ""))
    return result


def fetch_papers_historical_incremental() -> None:
    """增量更新：仅抓取尚未收录的 OpenAlex ID。"""
    existing: list[dict] = []
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    existing_ids = {p["id"] for p in existing}
    log.info(f"现有历史论文：{len(existing)} 篇")

    new_papers = [p for p in fetch_all_historical() if p["id"] not in existing_ids]
    log.info(f"新增历史论文：{len(new_papers)} 篇")

    if not new_papers:
        log.info("历史论文库无新增")
        return

    combined = existing + new_papers
    combined.sort(key=lambda p: p.get("date", ""))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"历史论文库已更新：共 {len(combined)} 篇 → {OUTPUT_PATH}")


if __name__ == "__main__":
    fetch_papers_historical_incremental()
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd scripts && python -m pytest tests/test_fetch_historical.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/fetch_papers_historical.py scripts/tests/ scripts/requirements.txt
git commit -m "feat: add fetch_papers_historical.py with incremental OpenAlex fetch"
```

---

## Task 3: `scripts/build_timeline.py`

**Files:**
- Create: `scripts/build_timeline.py`
- Create: `scripts/tests/test_build_timeline.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_build_timeline.py`:

```python
"""Tests for build_timeline utility functions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_timeline import get_decade, group_papers_by_topic_decade


def test_get_decade():
    assert get_decade(1975) == 1970
    assert get_decade(1980) == 1980
    assert get_decade(1989) == 1980
    assert get_decade(2023) == 2020


def test_group_papers_single_match():
    papers = [
        {"id": "W1", "year": 1982, "title": "casing treatment study",
         "topics_matched": ["机匣处理"], "tags": []},
    ]
    topics = [{"label": "机匣处理"}, {"label": "叶尖间隙"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["机匣处理"][1980] == ["W1"]
    assert "叶尖间隙" not in result or 1980 not in result.get("叶尖间隙", {})


def test_group_papers_uses_topics_matched_for_historical():
    # Historical paper (has topics_matched, no tags)
    papers = [
        {"id": "W2", "year": 1990, "title": "inlet distortion fan",
         "topics_matched": ["进气畸变"], "tags": []},
    ]
    topics = [{"label": "进气畸变"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["进气畸变"][1990] == ["W2"]


def test_group_papers_uses_tags_for_current():
    # Current paper (has tags, no topics_matched)
    papers = [
        {"id": "W3", "year": 2021, "title": "compressor tip clearance",
         "topics_matched": [], "tags": ["叶尖间隙"]},
    ]
    topics = [{"label": "叶尖间隙"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["叶尖间隙"][2020] == ["W3"]


def test_group_papers_deduplicates():
    papers = [
        {"id": "W4", "year": 1985, "topics_matched": ["机匣处理"], "tags": ["机匣处理"]},
    ]
    topics = [{"label": "机匣处理"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["机匣处理"][1980].count("W4") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd scripts && python -m pytest tests/test_build_timeline.py -v
```

Expected: `ImportError: No module named 'build_timeline'`

- [ ] **Step 3: Create `scripts/build_timeline.py`**

```python
"""
build_timeline.py
生成 data/timeline.json：按话题×年代统计论文数量，并用 DeepSeek 生成年代综述。
增量：已有综述的格子不重复调用 DeepSeek。
"""

import json
import logging
import os
from pathlib import Path
from openai import OpenAI

from config import FETCH_FROM_YEAR
from fetch_papers_historical import get_topics, DEFAULT_TOPICS

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

        # Merge topics_matched (historical) and tags (current) to cover both sources
        matched_labels = set(paper.get("topics_matched") or []) | set(paper.get("tags") or [])

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
    """调用 DeepSeek 生成年代综述，失败时返回空字符串。"""
    titles_text = "\n".join(f"- {t}" for t in titles[:30])  # 最多30篇标题
    prompt = (
        f"以下是{decade}年代关于"{topic_label}"的{len(titles)}篇论文标题：\n\n"
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
        log.warning(f"DeepSeek 生成综述失败 [{topic_label} {decade}s]: {e}")
        return ""


def build_timeline() -> None:
    """主函数：生成/更新 data/timeline.json。"""
    # 1. 加载论文
    historical: list[dict] = []
    if HISTORICAL_PATH.exists():
        historical = json.loads(HISTORICAL_PATH.read_text(encoding="utf-8"))
    current: list[dict] = []
    if CURRENT_PATH.exists():
        current = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))

    all_papers = historical + current
    log.info(f"加载论文：历史 {len(historical)} 篇 + 当前 {len(current)} 篇 = {len(all_papers)} 篇")

    # 2. 读取话题列表
    topics = get_topics()
    log.info(f"话题列表：{[t['label'] for t in topics]}")

    # 3. 按话题×年代分组
    paper_map = {p["id"]: p for p in all_papers}
    grouped = group_papers_by_topic_decade(all_papers, topics)

    # 4. 加载现有 timeline.json（用于增量摘要）
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

    # 5. 生成摘要（跳过已有摘要的格子）
    client = _get_deepseek_client()
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

    # 6. 写入 timeline.json
    from datetime import datetime, timezone
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd scripts && python -m pytest tests/test_build_timeline.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_timeline.py scripts/tests/test_build_timeline.py
git commit -m "feat: add build_timeline.py with incremental DeepSeek summaries"
```

---

## Task 4: Integrate into `scripts/run_pipeline.py`

**Files:**
- Modify: `scripts/run_pipeline.py`

The `main()` function at the bottom currently calls `run_papers_pipeline()`, `run_repos_pipeline()`, `write_meta()`. Add two more steps at the end.

- [ ] **Step 1: Add imports at the top of run_pipeline.py**

Find the existing import block (around line 12–14):
```python
from fetch_papers import fetch_all_papers
from process_with_ai import process_papers
from fetch_repos import fetch_all_repos, enrich_repos
from config import RESEARCH_GROUPS
```

Add two new imports immediately after:
```python
from fetch_papers_historical import fetch_papers_historical_incremental
from build_timeline import build_timeline
```

- [ ] **Step 2: Add calls inside main()**

Find `main()` (around line 235):
```python
def main() -> None:
    log.info("════════ 研究雷达流水线启动 ════════")

    run_papers_pipeline()
    run_repos_pipeline()
    write_meta()

    log.info("════════ 流水线完成 ════════")
```

Replace with:
```python
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
```

- [ ] **Step 3: Verify syntax**

```bash
cd scripts && python -c "import run_pipeline; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add scripts/run_pipeline.py
git commit -m "feat: add historical fetch + timeline build steps to pipeline"
```

---

## Task 5: Update `.github/workflows/pipeline.yml`

**Files:**
- Modify: `.github/workflows/pipeline.yml`

- [ ] **Step 1: Update the file_pattern in the auto-commit step**

Find the `file_pattern` line in the "Commit updated data" step:
```yaml
          file_pattern: data/papers.json data/repos.json data/groups.json data/meta.json
```

Replace with:
```yaml
          file_pattern: data/papers.json data/repos.json data/groups.json data/meta.json data/papers-historical.json data/timeline.json
```

- [ ] **Step 2: Verify the YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/pipeline.yml'))" 2>&1
```

Expected: no output (no error)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pipeline.yml
git commit -m "feat: add papers-historical.json and timeline.json to pipeline auto-commit"
```

---

## Task 6: `index.html` — TIMELINE tab + heatmap

**Files:**
- Modify: `index.html`

This task adds the TIMELINE nav button, the `tab-timeline` div, data loading, and heatmap rendering.

- [ ] **Step 1: Add TIMELINE nav button**

Find the nav buttons block (around line 1400–1406):
```html
    <button class="active" onclick="switchTab('papers')" id="btn-papers">PAPERS</button>
    <button onclick="switchTab('groups')" id="btn-groups">GROUPS</button>
    <button onclick="switchTab('repos')" id="btn-repos">REPOS</button>
    <button onclick="switchTab('chat')" id="btn-chat">AI CHAT</button>
    <button onclick="switchTab('manual')" id="btn-manual">MANUAL</button>
    <button onclick="switchTab('build')" id="btn-build">BUILD</button>
```

Replace with:
```html
    <button class="active" onclick="switchTab('papers')" id="btn-papers">PAPERS</button>
    <button onclick="switchTab('groups')" id="btn-groups">GROUPS</button>
    <button onclick="switchTab('repos')" id="btn-repos">REPOS</button>
    <button onclick="switchTab('timeline')" id="btn-timeline">TIMELINE</button>
    <button onclick="switchTab('chat')" id="btn-chat">AI CHAT</button>
    <button onclick="switchTab('manual')" id="btn-manual">MANUAL</button>
    <button onclick="switchTab('build')" id="btn-build">BUILD</button>
```

- [ ] **Step 2: Add `tab-timeline` HTML**

Find `<div id="tab-repos" style="display:none">` (around line 1647). It ends two lines later:
```html
<div id="tab-repos" style="display:none">
  <div class="repo-list" id="repo-list"></div>
</div>
```

Insert the following immediately after that closing `</div>`:

```html
<div id="tab-timeline" style="display:none; padding:20px 24px;">
  <div id="timeline-loading" style="color:var(--text3); font-family:'IBM Plex Mono',monospace; font-size:12px; padding:40px 0; text-align:center;">
    载入时间轴数据…
  </div>
  <div id="timeline-error" style="display:none; color:var(--rel5); font-family:'IBM Plex Mono',monospace; font-size:12px; padding:40px 0; text-align:center;"></div>
  <div id="timeline-heatmap" style="display:none;">
    <div style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--text3); letter-spacing:.08em; margin-bottom:16px;">
      论文数量热力图 · 1970–至今（点击格子查看年代综述和论文列表）
    </div>
    <div id="heatmap-grid" style="overflow-x:auto;"></div>
    <div style="margin-top:12px; display:flex; align-items:center; gap:8px; font-size:10px; color:var(--text3); font-family:'IBM Plex Mono',monospace;">
      <span>少</span>
      <div style="width:60px; height:8px; border-radius:2px; background:linear-gradient(to right, rgba(114,180,240,.1), rgba(114,180,240,.9));"></div>
      <span>多</span>
      <span style="margin-left:12px;">（颜色深浅按各话题行内部相对值缩放）</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add CSS for the heatmap**

Find the `</style>` closing tag (search for the last `</style>` before `</head>`). Insert these CSS rules just before it:

```css
/* ── Timeline heatmap ─────────────────────── */
.heatmap-table { border-collapse:separate; border-spacing:3px; font-family:'IBM Plex Mono',monospace; font-size:11px; }
.heatmap-table th { color:var(--text3); font-weight:400; padding:4px 8px; white-space:nowrap; text-align:center; }
.heatmap-table th.row-header { text-align:right; padding-right:12px; min-width:80px; }
.heatmap-cell {
  width:72px; height:36px; border-radius:4px; cursor:pointer;
  display:flex; align-items:center; justify-content:center;
  font-size:11px; font-family:'IBM Plex Mono',monospace; color:rgba(255,255,255,.7);
  transition:filter .15s, transform .1s;
  position:relative;
}
.heatmap-cell:hover { filter:brightness(1.3); transform:scale(1.06); z-index:1; }
.heatmap-cell.empty { background:rgba(255,255,255,.04); color:var(--text3); cursor:default; }
.heatmap-cell.empty:hover { filter:none; transform:none; }
```

- [ ] **Step 4: Update `switchTab` to include `'timeline'`**

Find `switchTab` function (around line 3457):
```javascript
function switchTab(tab) {
  ['papers','groups','repos','chat','build','manual'].forEach(t => {
```

Replace with:
```javascript
function switchTab(tab) {
  ['papers','groups','repos','timeline','chat','build','manual'].forEach(t => {
```

Also add a timeline-specific handler at the end of `switchTab`, after the existing `if (tab === 'chat')` block:
```javascript
  if (tab === 'timeline') {
    loadTimeline();
  }
```

- [ ] **Step 5: Add timeline state variables and color palette**

Find the section with other state variables (search for `let chatHistory`). Add before it:

```javascript
// ── Timeline state ──────────────────────────
let timelineData = null;         // parsed timeline.json
let historicalPapers = null;     // id → paper map from papers-historical.json
let timelineLoaded = false;

// Per-topic color palette (RGBA base, opacity applied per cell)
const TIMELINE_COLORS = [
  '114,180,240',  // blue
  '240,188,90',   // gold
  '110,216,154',  // green
  '196,140,240',  // purple
  '240,140,110',  // orange
  '140,200,240',  // light blue
];
```

- [ ] **Step 6: Add `loadTimeline()` function**

Add this function right after the timeline state variables block:

```javascript
async function loadTimeline() {
  if (timelineLoaded) return;

  const loadingEl = document.getElementById('timeline-loading');
  const errorEl   = document.getElementById('timeline-error');
  const heatmapEl = document.getElementById('timeline-heatmap');

  loadingEl.style.display = '';
  errorEl.style.display   = 'none';
  heatmapEl.style.display = 'none';

  try {
    const [tlRes, histRes] = await Promise.all([
      fetch('data/timeline.json'),
      fetch('data/papers-historical.json'),
    ]);

    if (!tlRes.ok) throw new Error('timeline.json 未找到，请先运行流水线');
    timelineData = await tlRes.json();

    historicalPapers = {};
    if (histRes.ok) {
      const arr = await histRes.json();
      arr.forEach(p => { historicalPapers[p.id] = p; });
    }

    timelineLoaded = true;
    loadingEl.style.display = 'none';
    renderHeatmap();
    heatmapEl.style.display = '';
  } catch (err) {
    loadingEl.style.display = 'none';
    errorEl.textContent = err.message || '加载失败';
    errorEl.style.display = '';
  }
}
```

- [ ] **Step 7: Add `renderHeatmap()` function**

Add immediately after `loadTimeline()`:

```javascript
function renderHeatmap() {
  if (!timelineData) return;
  const decades = timelineData.decades || [1970,1980,1990,2000,2010,2020];
  const topics  = timelineData.topics  || [];
  const grid    = document.getElementById('heatmap-grid');

  // Build table
  let html = '<table class="heatmap-table"><thead><tr>';
  html += '<th class="row-header"></th>';
  decades.forEach(d => { html += `<th>${d}s</th>`; });
  html += '</tr></thead><tbody>';

  topics.forEach((topic, ti) => {
    const color = TIMELINE_COLORS[ti % TIMELINE_COLORS.length];

    // Compute max count in this row for opacity scaling
    const counts = decades.map(d => (topic.decades[String(d)]?.count || 0));
    const maxCount = Math.max(...counts, 1);

    html += '<tr>';
    html += `<th class="row-header" style="color:rgba(${color},1)">${topic.label}</th>`;

    decades.forEach(d => {
      const cell = topic.decades[String(d)];
      if (!cell || cell.count === 0) {
        html += '<td><div class="heatmap-cell empty">—</div></td>';
        return;
      }
      const opacity = Math.max(0.12, cell.count / maxCount).toFixed(2);
      html += `<td><div class="heatmap-cell"
        style="background:rgba(${color},${opacity})"
        onclick="openTimelinePanel('${topic.label.replace(/'/g, "\\'")}', ${d})"
        title="${topic.label} · ${d}s · ${cell.count} 篇"
      >${cell.count}</div></td>`;
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  grid.innerHTML = html;
}
```

- [ ] **Step 8: Verify in browser**

Start the local server:
```bash
cd scripts && python server.py
```

Open http://localhost:5000, click TIMELINE tab. Expected:
- Loading message appears briefly
- Heatmap table renders (or error message if `data/timeline.json` missing — that's correct; data will be generated by pipeline)

- [ ] **Step 9: Commit**

```bash
git add index.html
git commit -m "feat: add TIMELINE tab with heatmap to index.html"
```

---

## Task 7: `index.html` — Drill-down slide panel

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Add `timeline-panel` HTML**

Find `<div id="topics-panel"` (around line 1510). Add the following panel HTML immediately **before** it (so z-index stacking is correct — timeline-panel at 502 goes after pipeline-panel at 500 and topics-panel at 501):

```html
<div id="timeline-panel" style="
  position:fixed; top:56px; right:0; bottom:0; width:420px;
  background:var(--bg2); border-left:1px solid var(--border2);
  display:flex; flex-direction:column;
  transform:translateX(100%); transition:transform .25s ease;
  z-index:502;
">
  <!-- 标题栏 -->
  <div style="padding:14px 18px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:10px; flex-shrink:0;">
    <span id="tl-panel-title" style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--gold); letter-spacing:.08em; flex:1;">—</span>
    <button onclick="closeTimelinePanel()" style="background:none; border:none; color:var(--text3); font-size:18px; cursor:pointer; line-height:1; padding:0 2px;">×</button>
  </div>
  <!-- 内容区（可滚动） -->
  <div id="tl-panel-body" style="flex:1; overflow-y:auto; padding:16px 18px; display:flex; flex-direction:column; gap:14px;">
  </div>
</div>
```

- [ ] **Step 2: Add `openTimelinePanel()` and `closeTimelinePanel()` functions**

Find `openTopicsPanel()` function. Add the following two functions immediately before it:

```javascript
function openTimelinePanel(topicLabel, decade) {
  const topic = timelineData?.topics?.find(t => t.label === topicLabel);
  const cell  = topic?.decades?.[String(decade)];
  if (!cell) return;

  document.getElementById('tl-panel-title').textContent =
    `${topicLabel} · ${decade}s`;

  const body = document.getElementById('tl-panel-body');
  body.innerHTML = '';

  // AI summary block
  const summaryDiv = document.createElement('div');
  summaryDiv.style.cssText = 'border-left:2px solid var(--gold); padding:10px 14px; background:var(--surface2); border-radius:0 4px 4px 0;';
  if (cell.summary) {
    summaryDiv.innerHTML = `
      <div style="color:var(--gold); font-size:10px; font-family:'IBM Plex Mono',monospace; letter-spacing:.06em; margin-bottom:6px;">✦ AI 年代综述</div>
      <div style="color:var(--text3); font-size:12px; line-height:1.7;">${cell.summary}</div>`;
  } else {
    summaryDiv.innerHTML = `<div style="color:var(--text3); font-size:11px; font-family:'IBM Plex Mono',monospace;">暂无综述，请重新运行流水线</div>`;
  }
  body.appendChild(summaryDiv);

  // Paper list header
  const headerDiv = document.createElement('div');
  headerDiv.style.cssText = 'color:var(--text3); font-size:10px; font-family:"IBM Plex Mono",monospace; letter-spacing:.06em;';
  headerDiv.textContent = `相关论文 · ${cell.count} 篇`;
  body.appendChild(headerDiv);

  // Gather papers: historical + current
  const allPapers = [];
  (cell.paper_ids || []).forEach(pid => {
    if (historicalPapers && historicalPapers[pid]) {
      allPapers.push({ ...historicalPapers[pid], _source: 'historical' });
    } else {
      const cp = papers.find(p => p.id === pid);
      if (cp) allPapers.push({ ...cp, _source: 'current' });
    }
  });
  allPapers.sort((a, b) => (a.year || 0) - (b.year || 0));

  const displayPapers = allPapers.slice(0, 20);
  const remaining = allPapers.length - 20;

  const listDiv = document.createElement('div');
  listDiv.style.cssText = 'display:flex; flex-direction:column; gap:6px;';

  displayPapers.forEach(p => {
    const item = document.createElement('div');
    item.style.cssText = 'background:var(--bg); border-radius:4px; padding:8px 10px; cursor:pointer;';
    const firstAuthor = (p.authors || [])[0] || '';
    const yearAuthor = `${p.year || ''}${firstAuthor ? ' · ' + firstAuthor.split(',')[0].split(' ').slice(-1)[0] : ''}`;

    if (p._source === 'current') {
      item.title = '点击跳转到论文详情';
      item.onclick = () => {
        closeTimelinePanel();
        switchTab('papers');
        setTimeout(() => {
          const el = document.getElementById('card-' + p.id);
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
      };
      item.innerHTML = `
        <div style="color:var(--text2); font-size:11px; margin-bottom:2px;">${yearAuthor}</div>
        <div style="color:var(--text3); font-size:11px; line-height:1.4;">${p.title}</div>`;
    } else {
      item.style.cursor = p.url ? 'pointer' : 'default';
      if (p.url) item.onclick = () => window.open(p.url, '_blank');
      item.innerHTML = `
        <div style="color:var(--text2); font-size:11px; margin-bottom:2px;">${yearAuthor}${p.url ? ' ↗' : ''}</div>
        <div style="color:var(--text3); font-size:11px; line-height:1.4;">${p.title}</div>`;
    }
    listDiv.appendChild(item);
  });

  if (remaining > 0) {
    const moreBtn = document.createElement('button');
    moreBtn.style.cssText = 'background:none; border:1px solid var(--border2); border-radius:4px; color:var(--text3); font-family:"IBM Plex Mono",monospace; font-size:10px; padding:6px; cursor:pointer; width:100%;';
    moreBtn.textContent = `显示全部 ${allPapers.length} 篇`;
    moreBtn.onclick = () => {
      // Show all remaining papers
      allPapers.slice(20).forEach(p => {
        const item = document.createElement('div');
        item.style.cssText = 'background:var(--bg); border-radius:4px; padding:8px 10px;';
        const firstAuthor = (p.authors || [])[0] || '';
        const yearAuthor = `${p.year || ''}${firstAuthor ? ' · ' + firstAuthor.split(',')[0].split(' ').slice(-1)[0] : ''}`;
        item.innerHTML = `
          <div style="color:var(--text2); font-size:11px; margin-bottom:2px;">${yearAuthor}${p._source === 'historical' && p.url ? ' ↗' : ''}</div>
          <div style="color:var(--text3); font-size:11px; line-height:1.4;">${p.title}</div>`;
        if (p._source === 'historical' && p.url) item.onclick = () => window.open(p.url, '_blank');
        if (p._source === 'current') {
          item.style.cursor = 'pointer';
          item.onclick = () => {
            closeTimelinePanel();
            switchTab('papers');
            setTimeout(() => {
              const el = document.getElementById('card-' + p.id);
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
          };
        }
        listDiv.insertBefore(item, moreBtn);
      });
      moreBtn.remove();
    };
    listDiv.appendChild(moreBtn);
  }

  body.appendChild(listDiv);
  document.getElementById('timeline-panel').style.transform = 'translateX(0)';
}

function closeTimelinePanel() {
  document.getElementById('timeline-panel').style.transform = 'translateX(100%)';
}
```

- [ ] **Step 3: Verify paper cards have id attribute**

Search for how paper cards are rendered in `render()`. Check that each card has `id="card-${p.id}"`:

```bash
grep -n "id=\"card-\|id=.card-" index.html | head -5
```

If the pattern exists, the scroll-to behavior will work. If not, find where paper cards are rendered (around line 2540) and confirm the id attribute.

- [ ] **Step 4: Verify in browser**

Start server, open TIMELINE tab, click any cell. Expected:
- Panel slides in from right
- Shows topic label + decade in header
- Shows AI summary block (or "暂无综述" if not yet generated)
- Shows paper list

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add timeline drill-down slide panel"
```

---

## Task 8: `index.html` — Wishlist

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Add wishlist panel HTML**

Find `</body>` at the very end of `index.html`. Add this block immediately before `</body>`:

```html
<!-- ── Wishlist ──────────────────────────────── -->
<!-- Floating button -->
<button onclick="openWishlist()" style="
  position:fixed; bottom:24px; right:24px; z-index:600;
  background:var(--bg2); border:1px solid var(--border2); border-radius:20px;
  color:var(--text2); font-family:'IBM Plex Mono',monospace; font-size:12px;
  padding:8px 16px; cursor:pointer; display:flex; align-items:center; gap:6px;
  box-shadow:0 2px 8px rgba(0,0,0,.4); transition:border-color .2s;
" onmouseover="this.style.borderColor='var(--gold)'" onmouseout="this.style.borderColor='var(--border2)'">
  📋 <span>愿望清单</span>
</button>

<!-- Wishlist slide panel -->
<div id="wishlist-panel" style="
  position:fixed; top:56px; right:0; bottom:0; width:380px;
  background:var(--bg2); border-left:1px solid var(--border2);
  display:flex; flex-direction:column;
  transform:translateX(100%); transition:transform .25s ease;
  z-index:601;
">
  <!-- Header -->
  <div style="padding:14px 18px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:10px; flex-shrink:0;">
    <span style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--gold); letter-spacing:.08em; flex:1;">文献愿望清单</span>
    <button onclick="closeWishlist()" style="background:none; border:none; color:var(--text3); font-size:18px; cursor:pointer; line-height:1; padding:0 2px;">×</button>
  </div>

  <!-- Add form -->
  <div style="padding:14px 18px; border-bottom:1px solid var(--border); flex-shrink:0;">
    <input id="wish-title-input" type="text" placeholder="论文标题 / 描述（必填）"
      style="width:100%; box-sizing:border-box; background:var(--bg); border:1px solid var(--border2); border-radius:4px;
             padding:8px 12px; color:var(--text); font-family:'IBM Plex Mono',monospace; font-size:12px; outline:none; margin-bottom:8px;" />
    <textarea id="wish-note-input" placeholder="备注（可选）" rows="2"
      style="width:100%; box-sizing:border-box; background:var(--bg); border:1px solid var(--border2); border-radius:4px;
             padding:8px 12px; color:var(--text); font-family:'IBM Plex Mono',monospace; font-size:12px; outline:none; resize:none; margin-bottom:8px;"></textarea>
    <button onclick="addWishlistItem()"
      style="width:100%; background:var(--gold-glow); border:1px solid var(--gold-dim); border-radius:4px;
             color:var(--gold); font-family:'IBM Plex Mono',monospace; font-size:11px; padding:8px; cursor:pointer;">
      + 添加
    </button>
    <div id="wish-error" style="display:none; color:var(--rel5); font-size:11px; font-family:'IBM Plex Mono',monospace; margin-top:6px;"></div>
  </div>

  <!-- List -->
  <div id="wish-list" style="flex:1; overflow-y:auto; padding:12px 18px; display:flex; flex-direction:column; gap:8px;"></div>
</div>
```

- [ ] **Step 2: Add wishlist JS**

Find `// ── AI Chat ──` comment. Add the following block immediately before it:

```javascript
// ── Wishlist ─────────────────────────────────

const LS_WISHLIST = 'ls_wishlist';

function getWishlist() {
  return lsGet(LS_WISHLIST, []);
}

function saveWishlist(items) {
  lsSet(LS_WISHLIST, items);
}

function openWishlist() {
  renderWishlist();
  document.getElementById('wishlist-panel').style.transform = 'translateX(0)';
  document.getElementById('wish-title-input').focus();
}

function closeWishlist() {
  document.getElementById('wishlist-panel').style.transform = 'translateX(100%)';
}

function renderWishlist() {
  const items = getWishlist();
  const listEl = document.getElementById('wish-list');

  if (items.length === 0) {
    listEl.innerHTML = '<div style="color:var(--text3); font-size:12px; font-family:\'IBM Plex Mono\',monospace; text-align:center; padding:24px 0;">暂无记录，把想找的文献记在这里</div>';
    return;
  }

  listEl.innerHTML = '';
  items.forEach((item, idx) => {
    const el = document.createElement('div');
    el.style.cssText = 'background:var(--bg); border-radius:6px; padding:10px 12px; position:relative;';
    const date = new Date(item.added_at).toLocaleDateString('zh-CN', { month:'short', day:'numeric', year:'numeric' });
    el.innerHTML = `
      <button onclick="deleteWishlistItem(${idx})"
        style="position:absolute; top:8px; right:8px; background:none; border:none; color:var(--text3); font-size:14px; cursor:pointer; line-height:1; padding:2px 4px;"
        title="删除">✕</button>
      <div style="color:var(--text2); font-size:12px; line-height:1.5; margin-right:20px;">${item.title}</div>
      ${item.note ? `<div style="color:var(--text3); font-size:11px; margin-top:4px; line-height:1.4;">${item.note}</div>` : ''}
      <div style="color:var(--text3); font-size:10px; font-family:'IBM Plex Mono',monospace; margin-top:6px;">${date}</div>`;
    listEl.appendChild(el);
  });
}

function addWishlistItem() {
  const titleEl = document.getElementById('wish-title-input');
  const noteEl  = document.getElementById('wish-note-input');
  const errEl   = document.getElementById('wish-error');
  const title = titleEl.value.trim();

  if (!title) {
    errEl.textContent = '请输入论文标题';
    errEl.style.display = '';
    return;
  }
  errEl.style.display = 'none';

  const items = getWishlist();
  items.unshift({
    id: Date.now().toString(),
    title,
    note: noteEl.value.trim(),
    added_at: new Date().toISOString(),
  });
  saveWishlist(items);

  titleEl.value = '';
  noteEl.value  = '';
  renderWishlist();
}

function deleteWishlistItem(idx) {
  const items = getWishlist();
  items.splice(idx, 1);
  saveWishlist(items);
  renderWishlist();
}
```

- [ ] **Step 3: Verify in browser**

Open any tab. Expected:
- 📋 愿望清单 button visible at bottom-right, on top of all content
- Click → panel slides in
- Type a title and click 添加 → item appears in list
- Click ✕ on an item → item is removed
- Refresh page → items persist (localStorage)
- Empty state message shows when list is empty

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add wishlist floating button and localStorage panel"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| `FETCH_FROM_YEAR_HISTORICAL = 1970` in config.py | Task 1 |
| `papers-historical.json` with all OpenAlex fields, no max limit | Task 2 |
| `topics_matched` computed at fetch time | Task 2 |
| Incremental fetch (skip existing IDs) | Task 2 |
| `build_timeline.py` groups papers by topic×decade | Task 3 |
| DeepSeek era summaries, incremental (skip existing) | Task 3 |
| `timeline.json` format with counts + paper_ids + summary | Task 3 |
| `run_pipeline.py` calls historical fetch + build_timeline | Task 4 |
| GitHub Actions commits new data files | Task 5 |
| TIMELINE tab in nav between REPOS and AI CHAT | Task 6 |
| Heatmap: topic rows × decade columns, color opacity scaled per row | Task 6 |
| Loading spinner; error if timeline.json missing | Task 6 |
| Drill-down panel slides from right on cell click | Task 7 |
| Panel shows AI summary + paper list sorted by year | Task 7 |
| Historical papers link to DOI in new tab | Task 7 |
| Current papers (2020+) click → scroll to paper in 论文 tab | Task 7 |
| Show first 20 papers with "显示全部 N 篇" toggle | Task 7 |
| Wishlist floating 📋 button always visible | Task 8 |
| Wishlist panel: add form (title required, note optional) | Task 8 |
| Each entry has delete button | Task 8 |
| Empty state message | Task 8 |
| `ls_wishlist` localStorage key | Task 8 |

All spec requirements covered. ✓
