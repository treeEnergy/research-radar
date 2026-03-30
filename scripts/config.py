# ─────────────────────────────────────────────
#  研究雷达 · 配置文件
#  按需修改关键词和分类标签
# ─────────────────────────────────────────────

# 搜索关键词（每个词会在所有目标期刊中搜索）
KEYWORDS = [
    "compressor tip clearance",
    "casing treatment stall margin",
    "axial compressor rotating stall",
    "compressor stability",
    "non-axisymmetric tip clearance",
    "compressor surge",
    "stall inception compressor",
    # 稳定性建模方向
    "actuator disk model compressor",
    "actuator disk model fan",
    "compressor stability model",
    "three-dimensional stability model turbomachinery",
    "Moore Greitzer model compressor",
    "body force model compressor",
    # 进气畸变方向
    "inlet distortion compressor",
    "circumferential distortion compressor",
    "inlet distortion fan",
    "total pressure distortion turbomachinery",
]

# 目标期刊（AIAA / ASME），按 ISSN 精准过滤
TARGET_JOURNALS = [
    {"name": "Journal of Turbomachinery",          "issn": "0889-504X"},
    {"name": "J. Eng. Gas Turbines and Power",     "issn": "0742-4795"},
    {"name": "Journal of Propulsion and Power",    "issn": "0748-4658"},
    {"name": "AIAA Journal",                        "issn": "0001-1452"},
]

# 只抓近几年的论文
FETCH_FROM_YEAR = 2020

# 历史论文起始年份（fetch_papers_historical.py 使用）
FETCH_FROM_YEAR_HISTORICAL = 1970

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
    {
        "name": "Greitzer Group",
        "institution": "MIT",
        "pis": ["Greitzer", "Choon Tan", "Tan C"],
    },
    {
        "name": "Nicole L. Key Group",
        "institution": "Purdue University",
        "pis": ["Nicole Key", "Nicole L. Key", "Key N"],
    },
    {
        "name": "Chunill Hah Group",
        "institution": "NASA Glenn",
        "pis": ["Chunill Hah", "Hah C"],
    },
    {
        "name": "Yanhui Wu Group",
        "institution": "Beijing Institute of Technology",
        "pis": ["Yanhui Wu", "Wu Y"],
    },
    {
        "name": "Jinfang Teng Group",
        "institution": "Shanghai Jiao Tong University",
        "pis": ["Jinfang Teng", "Teng J", "Mingmin Zhu"],
    },
    {
        "name": "Stephen Spence Group",
        "institution": "Queen's University Belfast",
        "pis": ["Stephen Spence", "Spence S"],
    },
]
