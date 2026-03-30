# ─────────────────────────────────────────────
#  研究雷达 · 配置文件
#  按需修改关键词和分类标签
# ─────────────────────────────────────────────

# 搜索关键词（每个词会在所有目标期刊中搜索）
# 原则：先用短词广搜，再用长词精搜，靠 AI 评分过滤不相关的
KEYWORDS = [
    # ── 叶尖间隙 ──
    "tip clearance",
    "tip leakage",
    "compressor tip clearance",
    # ── 机匣处理 ──
    "casing treatment",
    "stall margin",
    # ── 失速 / 喘振 / 稳定性 ──
    "rotating stall",
    "compressor surge",
    "stall inception",
    "compressor stability",
    # ── 稳定性建模 ──
    "actuator disk",
    "body force model",
    "Moore Greitzer",
    "streamline curvature",
    # ── 进气畸变 ──
    "distortion",
    "inlet distortion",
    "circumferential distortion",
    "radial distortion",
]

# 目标期刊（AIAA / ASME），按 ISSN 精准过滤
TARGET_JOURNALS = [
    {"name": "Journal of Turbomachinery",          "issn": "0889-504X"},
    {"name": "J. Eng. Gas Turbines and Power",     "issn": "0742-4795"},
    {"name": "Journal of Propulsion and Power",    "issn": "0748-4658"},
    {"name": "AIAA Journal",                        "issn": "0001-1452"},
]

# 历史期刊（前身），仅 fetch_papers_historical 使用
HISTORICAL_JOURNALS = [
    {"name": "J. Eng. for Power (→JEGTP前身)",     "issn": "0022-0825"},
    {"name": "J. Basic Engineering",                "issn": "0021-9223"},
]

# 只抓近几年的论文
FETCH_FROM_YEAR = 2020

# 历史论文起始年份（fetch_papers_historical.py 使用）
FETCH_FROM_YEAR_HISTORICAL = 1960

# GitHub 搜索词
GITHUB_KEYWORDS = [
    "turbomachinery CFD",
    "compressor stability",
    "actuator disk turbomachinery",
    "OpenFOAM turbomachinery",
    "axial compressor simulation",
]

# 分类标签（DeepSeek 从这里选，可自由扩展）
CATEGORIES = [
    "稳定性分析",
    "稳定性建模",
    "激盘/体力模型",
    "叶尖间隙",
    "机匣处理",
    "数值方法",
    "实验测量",
    "畸变进气",
    "失速/喘振机理",
    "其他",
]

# 每次最多抓取数量
MAX_PAPERS_PER_QUERY = 50   # 每个关键词每本期刊
MAX_REPOS = 20               # GitHub 仓库数

# 相关度阈值：低于此分数不写入最终 JSON
MIN_RELEVANCE = 2

# 重点追踪的课题组（PI 姓名列表用于匹配作者字段）
# 可自由添加，name 字段会显示在网页上
RESEARCH_GROUPS = [
    # ── 北美 ──
    {
        "name": "MIT GTL",
        "institution": "MIT",
        "pis": ["Greitzer", "Spakovszky", "C. S. Tan", "Choon Tan", "Paduano"],
    },
    {
        "name": "Purdue Compressor Lab",
        "institution": "Purdue University",
        "pis": ["Nicole Key", "Nicole L. Key", "Berdanier", "Sanford Fleeter"],
    },
    {
        "name": "NASA Glenn",
        "institution": "NASA Glenn Research Center",
        "pis": ["Chunill Hah", "Adamczyk"],
    },
    {
        "name": "Polytechnique Montreal",
        "institution": "Polytechnique Montreal",
        "pis": ["Huu Duc Vo", "Alain Batailly"],
    },
    # ── 欧洲 ──
    {
        "name": "Cambridge Whittle Lab",
        "institution": "University of Cambridge",
        "pis": ["Cumpsty", "Hodson", "I. J. Day", "Cesare A. Hall", "Paul G. Tucker"],
    },
    {
        "name": "Oxford Thermofluids",
        "institution": "University of Oxford",
        "pis": ["L. He", "Thomas Povey"],
    },
    {
        "name": "Imperial Aeroelasticity",
        "institution": "Imperial College London",
        "pis": ["Mehdi Vahdati"],
    },
    {
        "name": "ETH Zurich LEC",
        "institution": "ETH Zurich",
        "pis": ["Reza S. Abhari"],
    },
    {
        "name": "Ecole Centrale Lyon LMFA",
        "institution": "Ecole Centrale de Lyon",
        "pis": ["Xavier Ottavy", "Christoph Brandstetter", "Fabrice Thouverez"],
    },
    {
        "name": "TU Dresden",
        "institution": "TU Dresden",
        "pis": ["Ronald Mailach"],
    },
    {
        "name": "Cranfield Propulsion",
        "institution": "Cranfield University",
        "pis": ["David G. MacManus", "Vassilios Pachidis"],
    },
    {
        "name": "Bath Sealing Group",
        "institution": "University of Bath",
        "pis": ["James A. Scobie", "Gary D. Lock", "Carl M. Sangan"],
    },
    {
        "name": "ITP Aero / UPM",
        "institution": "ITP Aero / Univ. Politecnica de Madrid",
        "pis": ["Roque Corral"],
    },
    # ── 中国 ──
    {
        "name": "Beihang BUAA",
        "institution": "Beihang University",
        "pis": ["Xiaofeng Sun", "Dakun Sun", "Xu Dong"],
    },
    {
        "name": "Tsinghua Turbo Lab",
        "institution": "Tsinghua University",
        "pis": ["Xinqian Zheng"],
    },
    {
        "name": "CAS IET",
        "institution": "Chinese Academy of Sciences",
        "pis": ["Juan Du"],
    },
    {
        "name": "Peking University",
        "institution": "Peking University",
        "pis": ["Chao Zhou"],
    },
    {
        "name": "BIT Wu Group",
        "institution": "Beijing Institute of Technology",
        "pis": ["Yanhui Wu"],
    },
    {
        "name": "SJTU Teng Group",
        "institution": "Shanghai Jiao Tong University",
        "pis": ["Jinfang Teng", "Mingmin Zhu"],
    },
    # ── 工业界 ──
    {
        "name": "Penn State (historical)",
        "institution": "Penn State University",
        "pis": ["Lakshminarayana"],
    },
    {
        "name": "Ferrara / Parma",
        "institution": "Univ. Ferrara / Univ. Parma",
        "pis": ["Michele Pinelli", "Mirko Morini"],
    },
    {
        "name": "GE Aviation",
        "institution": "GE Aviation",
        "pis": ["A. R. Wadia"],
    },
    {
        "name": "Kurz & Brun (Industrial GT)",
        "institution": "Solar Turbines / Elliott Group",
        "pis": ["Rainer Kurz", "Klaus Brun"],
    },
]
