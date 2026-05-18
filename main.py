#!/usr/bin/env python3
"""YOUCAT Vibe — 天主教青年教理 AI 伦理向导
FastAPI 后端 + DeepSeek RAG 问答"""

import json
import os
import random
import re
import sys
import requests
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="YOUCAT Vibe")

# CORS —— 防止浏览器拦截
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 静态文件挂载（离线地图瓦片） ──────────────────────
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
TILES_DIR = STATIC_DIR / "tiles"
TILES_DIR.mkdir(exist_ok=True)
# 放一个占位文件确保目录存在
(TILES_DIR / ".gitkeep").touch(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── 配置 ──────────────────────────────────────────────
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not API_KEY:
    print("[YOUCAT Vibe] 警告: DEEPSEEK_API_KEY 环境变量未设置!")
else:
    print(f"[YOUCAT Vibe] API Key: {API_KEY[:12]}...{API_KEY[-4:]}")
API_URL = "https://api.deepseek.com/chat/completions"
JSON_PATH = Path(__file__).parent / "youcat_master.json"
TOP_K = 8

# ── 加载知识库 ─────────────────────────────────────────
with open(JSON_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)
entries = db["entries"]
print(f"[YOUCAT Vibe] 已加载 {len(entries)} 条教理数据")
print(f"[YOUCAT Vibe] API URL: {API_URL}")
print(f"[YOUCAT Vibe] CORS: enabled")


# ── RAG 检索 ──────────────────────────────────────────
def search_entries(query: str, top_k: int = TOP_K) -> list:
    """简单关键词匹配检索，按相关度排序。"""
    keywords = _tokenize(query)
    if not keywords:
        return random.sample(entries, min(top_k, len(entries)))

    scored = []
    for e in entries:
        text = " ".join([
            e.get("concept", ""),
            e.get("theological_definition", ""),
            e.get("ethical_application", ""),
            e.get("topic_category", ""),
        ])
        score = sum(text.count(kw) for kw in keywords)
        if score > 0:
            scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:top_k]]


def _tokenize(text: str) -> list:
    """中文简易分词：取 2-4 字词 + 英文单词。"""
    tokens = []
    # 英文单词
    tokens.extend(re.findall(r"[a-zA-Z]{2,}", text.lower()))
    # 中文 bigram / trigram
    cn = re.sub(r"[^一-鿿]", "", text)
    for size in [4, 3, 2]:
        for i in range(len(cn) - size + 1):
            tokens.append(cn[i:i + size])
    return tokens


# ── DeepSeek API 调用 ──────────────────────────────────
def get_system_prompt(lang: str = "zh") -> str:
    """根据语言返回对应的系统提示词。"""
    if lang == "en":
        return (
            "You are an AI mentor named 'Catamicus', warm, kind, and knowledgeable. "
            "You specialize in answering young people's questions about the Catholic faith and ethical life.\n\n"
            "Iron rule — You must ONLY answer based on the YOUCAT knowledge fragments provided below:\n"
            "1. First carefully read all knowledge fragments, find the most relevant content to the user's question\n"
            "2. Answer with a warm, elder-like tone, transforming catechetical knowledge into guidance for young people\n"
            "3. If the provided fragments are insufficient, honestly say: 'My child, regarding this question, "
            "the youth catechism materials I have at hand are not sufficient to give a complete answer. "
            "I suggest you consult a priest or refer to the full Catechism of the Catholic Church.'\n"
            "4. Reply in natural, conversational English, as if sitting down for coffee with a young person\n"
            "5. Appropriately quote Bible verses or saint sayings from the knowledge fragments\n"
            "6. Keep replies within 300 words, concise and impactful"
        )
    return (
        "你是一位名叫「卡米克斯 (Catamicus)」的 AI 导师，温暖、慈祥、博学。"
        "你专门为年轻人解答有关天主教信仰和伦理生活的疑惑。\n\n"
        "铁律——你只能基于下面提供的 YOUCAT 知识片段来回答问题：\n"
        "1. 先仔细阅读所有知识片段，找到与用户问题最相关的内容\n"
        "2. 用温暖如长者般的语气，将这些教理知识转化为对年轻人的开导\n"
        "3. 如果提供的知识片段不足以回答问题，请诚实地说「孩子，关于这个问题，"
        "我手头的青年教理资料还不足以给出完整的回答。建议你请教一位神父或查阅完整的天主教教理。」\n"
        "4. 回复使用自然的口语化中文，像在跟一位年轻人坐下来喝咖啡聊天\n"
        "5. 适当引用知识片段中的圣经经文或圣人语录\n"
        "6. 回复控制在 300 字以内，简洁有力"
    )


def ask_deepseek(question: str, context_entries: list, lang: str = "zh") -> str:
    """将检索到的上下文 + 用户问题发送给 DeepSeek。"""
    # 构建上下文
    ctx_parts = []
    for i, e in enumerate(context_entries, 1):
        ctx_parts.append(
            f"[{i}] 类别：{e.get('topic_category','')}\n"
            f"概念：{e.get('concept','')}\n"
            f"教理定义：{e.get('theological_definition','')}\n"
            f"伦理应用：{e.get('ethical_application','')}\n"
            f"圣经/历史：{e.get('scripture_and_history','')}"
        )
    context = "\n\n".join(ctx_parts)

    user_msg = (
        f"── 知识库参考片段 ──\n{context}\n\n"
        f"── 年轻人的提问 ──\n{question}\n\n"
        f"请基于以上知识片段，以卡米克斯 (Catamicus) 的身份温暖地回答这位年轻人。"
    )

    session = requests.Session()
    session.trust_env = False

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": get_system_prompt(lang)},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.7,
        "max_tokens": 800,
    }

    try:
        resp = session.post(API_URL, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }, json=payload, timeout=90, proxies={})

        # ── 调试日志 ──
        print(f"[DeepSeek] status={resp.status_code}", flush=True)
        if resp.status_code != 200:
            print(f"[DeepSeek] ERROR body: {resp.text[:500]}", flush=True)

        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        print(f"[DeepSeek] OK, answer length={len(answer)}", flush=True)
        return answer
    except Exception as e:
        print(f"[DeepSeek] EXCEPTION: {e}", flush=True)
        return f"孩子，抱歉，我暂时无法连接到思考的源泉。请稍后再试。（错误：{e}）"


# ── API 路由 ───────────────────────────────────────────

def _has_chinese(text: str) -> bool:
    """判断文本是否包含中文字符。"""
    for ch in text:
        if '一' <= ch <= '鿿':
            return True
    return False


@app.get("/api/quote")
async def daily_quote(lang: str = Query("zh", min_length=2, max_length=2)):
    """随机返回一条 ethical_application 作为日签箴言，按语言过滤。"""
    # 优先选有内容的 ethical_application
    pool = [e for e in entries if len(e.get("ethical_application", "")) > 30]
    if not pool:
        pool = entries

    # 按语言过滤
    if lang == 'en':
        lang_pool = [e for e in pool if not _has_chinese(e.get("ethical_application", ""))]
    else:
        lang_pool = [e for e in pool if _has_chinese(e.get("ethical_application", ""))]

    # 如果过滤后为空，回退到全部池
    if not lang_pool:
        lang_pool = pool

    chosen = random.choice(lang_pool)
    print(f"[Quote] lang={lang}, pool={len(lang_pool)}/{len(pool)}, concept={chosen.get('concept','')}", flush=True)
    return {
        "text": chosen["ethical_application"],
        "concept": chosen.get("concept", ""),
        "category": chosen.get("topic_category", ""),
        "reference_id": chosen.get("reference_id", ""),
    }


@app.get("/api/calendar/{year}/{month}")
async def get_calendar(year: int, month: int):
    """返回指定年月的礼仪日历，数据来自本地 calender/calendar_{year}.json。"""
    cal_file = (Path(__file__).parent / "calender" / f"calendar_{year}.json").resolve()
    print(f"[Calendar] 尝试读取: {cal_file}", flush=True)
    if not cal_file.exists():
        print(f"[Calendar] 文件不存在: {cal_file}", flush=True)
        return {"days": {}, "year": year, "month": month}
    try:
        with open(cal_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[Calendar] 读取失败: {e}", flush=True)
        return {"days": {}, "year": year, "month": month}

    litcal = data.get("litcal", [])
    days = {}
    for event in litcal:
        if event.get("month") == month:
            day = str(event.get("day", 1))
            # 取第一个颜色值
            color = "white"
            if event.get("color") and len(event["color"]) > 0:
                color = event["color"][0]
            days.setdefault(day, []).append({
                "name": event.get("name", ""),
                "color": color,
                "grade": event.get("grade_lcl", ""),
                "season": event.get("liturgical_season_lcl", ""),
            })
    print(f"[Calendar] {year}-{month:02d}: {sum(len(v) for v in days.values())} celebrations on {len(days)} days", flush=True)
    return {"days": days, "year": year, "month": month}


@app.post("/api/chat")
async def chat(req: Request):
    """RAG 问答接口。"""
    body = await req.json()
    question = body.get("question", "").strip()
    lang = body.get("lang", "zh").strip()
    print(f"[Chat] 收到问题: {question[:80]}... lang={lang}", flush=True)

    if not question or len(question) < 2:
        return JSONResponse({"answer": "孩子，你想问什么呢？请多说一些。"})

    # RAG 检索
    context = search_entries(question)
    print(f"[Chat] RAG 检索到 {len(context)} 条相关知识", flush=True)

    if not context:
        return JSONResponse({
            "answer": "孩子，我在教理数据库中没找到与你问题直接相关的内容。试试换个说法？"
        })

    # 调用 DeepSeek
    answer = ask_deepseek(question, context, lang)
    # 收集上下文中的地理位置标签
    loc_tags = []
    for e in context:
        tags = e.get("location_tags", [])
        for t in tags:
            if t and t not in loc_tags:
                loc_tags.append(t)
    print(f"[Chat] 回答已生成，长度={len(answer)}, locations={loc_tags}", flush=True)
    return {"answer": answer, "refs": len(context), "locations": loc_tags}


@app.get("/api/search")
async def search(q: str = Query("", min_length=1)):
    """全局模糊搜索 —— 匹配 concept / theological_definition / ethical_application。"""
    keywords = _tokenize(q)
    if not keywords:
        return {"results": []}

    scored = []
    for e in entries:
        haystack = " ".join([
            e.get("concept", ""),
            e.get("theological_definition", ""),
            e.get("ethical_application", ""),
            e.get("topic_category", ""),
        ])
        score = sum(haystack.count(kw) for kw in keywords)
        if score > 0:
            scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    # 最多返回 20 条
    results = []
    for _, e in scored[:20]:
        results.append({
            "topic_category": e.get("topic_category", ""),
            "concept": e.get("concept", ""),
            "reference_id": e.get("reference_id", ""),
            "theological_definition": (e.get("theological_definition", "") or "")[:200],
            "ethical_application": (e.get("ethical_application", "") or "")[:200],
            "location_tags": e.get("location_tags", []),
        })
    return {"results": results}


# ── 前端页面 ───────────────────────────────────────────
TPL_PATH = Path(__file__).parent / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    return TPL_PATH.read_text(encoding="utf-8")


# ── 启动入口 ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
