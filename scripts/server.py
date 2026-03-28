"""
server.py
替代 python -m http.server，提供静态文件服务 + 标注 API + 流水线触发 API。

运行方式：cd scripts && python server.py
访问：http://localhost:8000
"""

import json
import os
import subprocess
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response, stream_with_context
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
DATA_DIR  = BASE_DIR / "data"

# 加载 .env（本地开发用）
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)


# ── 静态文件 ──────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/data/<path:filename>")
def data_files(filename):
    return send_from_directory(DATA_DIR, filename)


# ── 标注 API ──────────────────────────────────

def load_annotations() -> dict:
    path = DATA_DIR / "annotations.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def save_annotations(data: dict) -> None:
    path = DATA_DIR / "annotations.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@app.route("/api/annotate", methods=["POST"])
def annotate():
    body     = request.get_json(force=True)
    paper_id = body.get("paper_id", "").strip()
    if not paper_id:
        return jsonify({"ok": False, "error": "missing paper_id"}), 400

    annotations = load_annotations()
    entry = annotations.get(paper_id, {})

    # 更新 note
    if "note" in body:
        note = body["note"].strip()
        if note:
            entry["note"]    = note
            entry["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            entry.pop("note", None)
            entry.pop("updated", None)

    # 更新已读状态
    if "read" in body:
        if body["read"]:
            entry["read"]    = True
            entry["read_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            entry.pop("read", None)
            entry.pop("read_at", None)

    if entry:
        annotations[paper_id] = entry
    else:
        annotations.pop(paper_id, None)

    save_annotations(annotations)
    return jsonify({"ok": True, "entry": entry})


@app.route("/api/annotations")
def get_annotations():
    return jsonify(load_annotations())


# ── 自定义课题组 API ───────────────────────────

CUSTOM_GROUPS_PATH = DATA_DIR / "custom_groups.json"

def load_custom_groups() -> list:
    if CUSTOM_GROUPS_PATH.exists():
        return json.loads(CUSTOM_GROUPS_PATH.read_text(encoding="utf-8"))
    return []

def save_custom_groups(data: list) -> None:
    CUSTOM_GROUPS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@app.route("/api/groups/save", methods=["POST"])
def groups_save():
    """新增或更新一个自定义 group。replaces 字段指向被替换的原始名称（如 ★ Dakun Sun）。"""
    body        = request.get_json(force=True)
    name        = body.get("name", "").strip()
    institution = body.get("institution", "").strip()
    pis_raw     = body.get("pis", "")
    replaces    = body.get("replaces", "").strip()   # 被替换的原始 group 名
    if not name:
        return jsonify({"ok": False, "error": "missing name"}), 400
    pis = [p.strip() for p in pis_raw.replace("，", ",").split(",") if p.strip()]
    groups = load_custom_groups()
    # 移除同名或同 replaces 的旧条目，避免重复
    groups = [g for g in groups
              if g["name"] != name and g.get("replaces") != replaces]
    entry = {"name": name, "institution": institution, "pis": pis, "custom": True}
    if replaces:
        entry["replaces"] = replaces
    groups.append(entry)
    save_custom_groups(groups)
    return jsonify({"ok": True})


@app.route("/api/groups/delete", methods=["POST"])
def groups_delete():
    body = request.get_json(force=True)
    name = body.get("name", "").strip()
    groups = load_custom_groups()
    groups = [g for g in groups if g["name"] != name]
    save_custom_groups(groups)
    return jsonify({"ok": True})


@app.route("/api/groups/custom")
def groups_custom():
    return jsonify(load_custom_groups())


# ── 流水线 API ─────────────────────────────────

_pipeline_lock   = threading.Lock()
_pipeline_running = False
_pipeline_logs   = deque(maxlen=200)   # 最近 200 行日志
_pipeline_result = {"status": "idle"}  # idle / running / done / error


def _run_pipeline_thread():
    global _pipeline_running, _pipeline_result
    script = Path(__file__).parent / "run_pipeline.py"
    _pipeline_logs.clear()
    _pipeline_logs.append("[系统] 流水线启动…")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(Path(__file__).parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            _pipeline_logs.append(line.rstrip())
        proc.wait()
        if proc.returncode == 0:
            _pipeline_logs.append("[系统] 流水线完成 ✓")
            _pipeline_result = {"status": "done"}
        else:
            _pipeline_logs.append(f"[系统] 流水线异常退出（code {proc.returncode}）")
            _pipeline_result = {"status": "error"}
    except Exception as e:
        _pipeline_logs.append(f"[系统] 启动失败：{e}")
        _pipeline_result = {"status": "error"}
    finally:
        _pipeline_running = False


@app.route("/api/pipeline/run", methods=["POST"])
def pipeline_run():
    global _pipeline_running, _pipeline_result
    with _pipeline_lock:
        if _pipeline_running:
            return jsonify({"ok": False, "error": "already running"}), 409
        _pipeline_running = True
        _pipeline_result  = {"status": "running"}
    t = threading.Thread(target=_run_pipeline_thread, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/pipeline/status")
def pipeline_status():
    return jsonify({
        "running": _pipeline_running,
        "status":  _pipeline_result.get("status", "idle"),
        "logs":    list(_pipeline_logs),
    })


# ── AI 对话 API ───────────────────────────────

CHAT_SYSTEM = """你是一个航空发动机压气机气动热力学领域的研究助手。
用户的研究方向：压气机稳定性、叶尖间隙、机匣处理、进气畸变、稳定性建模（激盘/体力模型）。

你有权访问用户的论文库（已在下方提供相关论文摘要）。
优先基于论文库回答问题，不要编造不在库中的论文信息。
如果论文库中没有找到相关内容，明确告知用户，并建议他们使用"更新检索"抓取更多论文。
回答简洁、专业，使用中文，可适当引用论文标题。"""


def _search_papers_local(query: str, papers: list[dict], top_k: int = 12) -> list[dict]:
    """关键词匹配，搜索多个字段，只返回真正命中查询词的论文"""
    q = query.lower()
    # 同时处理英文单词和中文词（中文按字符切，英文按空格切）
    en_words = [w for w in q.split() if len(w) > 2 and w.isascii()]
    # 中文关键词：提取长度 >= 2 的连续中文片段
    import re
    zh_words = re.findall(r'[\u4e00-\u9fff]{2,}', q)
    keywords = en_words + zh_words

    # 没有有效关键词（如纯问候）→ 不附加论文上下文
    if not keywords:
        return []

    scored = []
    for p in papers:
        # 搜索范围：标题、摘要、中文综述、方法、创新点、标签、作者
        fields = [
            p.get("title", ""),
            p.get("abstract", "")[:500],
            p.get("summary_zh", ""),
            p.get("method", ""),
            p.get("innovation", ""),
            " ".join(p.get("tags", [])),
            " ".join(p.get("authors", [])[:3]),
        ]
        text = " ".join(fields).lower()

        # 关键词命中次数（英文词权重 ×2，更精确）
        kw_score = sum(text.count(kw) * (2 if kw.isascii() else 1) for kw in keywords)

        # 必须至少命中一个关键词才算相关
        if kw_score == 0:
            continue

        # 相关度分数加权（1分=小加成，不让相关度掩盖关键词命中）
        total = kw_score * 10 + p.get("relevance", 0)
        scored.append((total, p))

    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:top_k]]


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    if not message:
        return jsonify({"ok": False, "error": "empty message"}), 400

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return jsonify({"ok": False, "error": "DEEPSEEK_API_KEY 未设置，请检查 .env 文件"}), 500

    # 加载论文库
    papers_path = DATA_DIR / "papers.json"
    papers = json.loads(papers_path.read_text(encoding="utf-8")) if papers_path.exists() else []

    # 库的全局摘要（始终注入，让 AI 对整体组成有认知）
    from collections import Counter
    author_counter: Counter = Counter()
    for p in papers:
        for a in p.get("authors", []):
            author_counter[a] += 1
    top_authors = [f"{a}（{c}篇）" for a, c in author_counter.most_common(30)]
    rel_dist = Counter(p.get("relevance", 0) for p in papers)
    library_summary = (
        f"论文库概况：共 {len(papers)} 篇，"
        f"相关度分布：5分={rel_dist.get(5,0)}篇 4分={rel_dist.get(4,0)}篇 3分={rel_dist.get(3,0)}篇 2分={rel_dist.get(2,0)}篇。\n"
        f"高频作者（前30，含中英文）：{', '.join(top_authors)}"
    )

    # 针对当前问题检索最相关的论文
    relevant = _search_papers_local(message, papers, top_k=12)

    context_parts = [library_summary]
    if relevant:
        lines = []
        for p in relevant:
            parts = [f"【{p['title']}】({p.get('date','')[:4]}, 相关度{p.get('relevance','?')}, {p.get('venue','')})"]
            parts.append(f"  作者: {', '.join(p.get('authors',[]))}")
            parts.append(f"  中文综述: {p.get('summary_zh','')}")
            if p.get('method'):
                parts.append(f"  研究方法: {p['method']}")
            if p.get('innovation'):
                parts.append(f"  创新点: {p['innovation']}")
            if p.get('conclusions'):
                parts.append(f"  主要结论: {p['conclusions']}")
            if p.get('limitations'):
                parts.append(f"  局限性: {p['limitations']}")
            if p.get('tags'):
                parts.append(f"  标签: {', '.join(p['tags'])}")
            lines.append("\n".join(parts))
        context_parts.append("以下是与当前问题最相关的论文：\n\n" + "\n\n".join(lines))

    messages = [{"role": "system", "content": CHAT_SYSTEM}]
    messages.append({"role": "system", "content": "\n\n".join(context_parts)})
    for h in history[-6:]:  # 保留最近 6 轮对话
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    def generate():
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=1200,
            )
            # 先发送检索到的论文信息
            meta = json.dumps({
                "type": "meta",
                "count": len(relevant),
                "titles": [p["title"][:60] for p in relevant],
            }, ensure_ascii=False)
            yield f"data: {meta}\n\n"

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield f"data: {json.dumps({'type': 'text', 'text': delta}, ensure_ascii=False)}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    print("研究雷达服务启动：http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)
