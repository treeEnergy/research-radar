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
try:
    from config import HISTORICAL_JOURNALS
except ImportError:
    HISTORICAL_JOURNALS = []

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
        "tip clearance", "tip leakage", "tip gap", "leakage vortex", "leakage flow",
        "blade tip", "tip vortex",
    ]},
    {"label": "机匣处理", "terms": [
        "casing treatment stall margin", "casing treatment",
        "casing groove", "casing slot", "shroud treatment", "endwall treatment",
    ]},
    {"label": "压缩机稳定性", "terms": [
        "axial compressor rotating stall", "compressor stability",
        "compressor surge", "stall inception compressor",
        "rotating stall", "stall inception", "surge", "stall margin",
        "post-stall", "spike", "modal wave", "stall cell",
        "active control stall", "stall recovery", "hysteresis",
        "instability", "stability",
    ]},
    {"label": "稳定性建模", "terms": [
        "actuator disk model compressor", "actuator disk model fan",
        "compressor stability model", "three-dimensional stability model turbomachinery",
        "Moore Greitzer model compressor", "body force model compressor",
        "actuator disk", "actuator disc", "body force model", "body force",
        "moore-greitzer", "moore greitzer", "throughflow model",
        "streamline curvature", "reduced order model", "meanline",
    ]},
    {"label": "进气畸变", "terms": [
        "inlet distortion compressor", "circumferential distortion compressor",
        "inlet distortion fan", "total pressure distortion turbomachinery",
        "inlet distortion", "circumferential distortion", "total pressure distortion",
        "distortion", "non-uniform inlet", "nonuniform inlet",
    ]},
    {"label": "跨音速/激波", "terms": [
        "transonic compressor", "transonic fan", "transonic rotor",
        "shock wave", "shock structure", "passage shock", "bow shock",
        "supersonic compressor", "transonic cascade", "transonic stage",
        "transonic", "shock",
    ]},
    {"label": "叶片气动设计", "terms": [
        "blade design", "airfoil design", "cascade", "blade row",
        "controlled diffusion", "swept blade", "blade sweep", "lean",
        "optimization", "blade profile", "blade shape",
    ]},
    {"label": "离心压气机", "terms": [
        "centrifugal compressor", "centrifugal impeller", "radial compressor",
        "vaneless diffuser", "vaned diffuser", "inducer",
        "centrifugal", "impeller", "diffuser",
    ]},
    {"label": "非定常流动", "terms": [
        "unsteady flow", "unsteady", "time-resolved", "rotor-stator interaction",
        "wake", "clocking", "deterministic stress",
    ]},
    {"label": "气弹/振动", "terms": [
        "flutter", "aeroelastic", "forced response", "mistuning",
        "blade vibration", "aeromechanics", "aeroelasticity",
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
    all_journals = TARGET_JOURNALS + HISTORICAL_JOURNALS
    tasks = [
        (kw, journal["issn"], journal["name"])
        for journal in all_journals
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
            try:
                for p in future.result():
                    all_papers[p["id"]] = p
            except Exception as e:
                name, kw = futures[future]
                log.warning(f"历史抓取任务失败 [{name} / {kw}]: {e}")

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
