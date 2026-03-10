import os
import glob
import json
import re
import asyncio
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core_rag import BaseRAGManager

load_dotenv()
app = FastAPI(title="Universe Manager API (Standalone)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_ROOT = os.getenv("AEGIS_DATA_PATH", "./data")
rag_manager = BaseRAGManager(DATA_ROOT)

@app.get("/api/health")
async def health():
    return {"status": "ok", "data_path": DATA_ROOT}

# ============================
# API: Query Seed Phrases
# ============================
QUERY_SEED_PHRASES = {
    "回忆型": ["你还记得", "你还记不记得", "我说过", "我曾经说过", "我们之间", "上一次", "那一次", "当时"],
    "情感型": ["你对我的", "你喜不喜欢", "你有没有想过", "你最在乎的", "你的感受"],
    "事件型": ["发生了什么", "那件事", "我们做过", "一起经历的", "你告诉过我"],
    "地点型": ["在书房", "在旧申府", "在申都", "那个地方"],
    "时间型": ["第一次见面", "刚见面时", "很久以前", "那个下午", "刚认识时"],
}

@app.get("/api/universe/query_seed_phrases")
async def get_query_seed_phrases():
    return JSONResponse({"categories": QUERY_SEED_PHRASES})

# ============================
# API: Diagnose Clean
# ============================
class DiagnoseRequest(BaseModel):
    raw_text: str
    user_msg: str = ""

@app.post("/api/universe/diagnose_clean")
async def diagnose_clean(req: DiagnoseRequest):
    raw = req.raw_text.strip()
    if not raw:
        return JSONResponse({"error": "raw_text 不能为空"}, status_code=400)

    scores = {}
    bold_matches = re.findall(r'\*{1,3}[^\*]{2,60}\*{1,3}', raw)
    scores["bold_action"] = len(bold_matches) * 2
    jp_matches = re.findall(r'[「『].{2,60}[」』]', raw)
    scores["japanese_quote"] = len(jp_matches) * 2
    paren_matches = re.findall(r'[（(][^\)）]{2,40}[)）]', raw)
    scores["parenthesis_thought"] = len(paren_matches) * 2
    forum_matches = re.findall(r'[【\[].{2,20}[】\]]', raw)
    scores["forum_style"] = len(forum_matches) * 3
    code_matches = re.findall(r'```[a-z]*', raw)
    scores["markdown_noise"] = len(code_matches) * 5
    html_matches = re.findall(r'<[a-zA-Z_]+[^>]*>', raw)
    scores["html_noise"] = len(html_matches) * 4

    style_meta = {
        "bold_action": {"name": "旁白+对话（*星号*加粗）", "desc": "以 *动作* 表示行为，常见于中文RP"},
        "japanese_quote": {"name": "日式引号纯对话", "desc": "用「台词」表示对话"},
        "parenthesis_thought": {"name": "括号内心戏", "desc": "用（想法）表示人物内心"},
        "forum_style": {"name": "论坛体/小剧场", "desc": "含【小剧场】【标题】等元标记"},
        "markdown_noise": {"name": "含 Markdown 代码块", "desc": "混有 ```html 等渲染块"},
        "html_noise": {"name": "含 HTML 标签", "desc": "混有自定义标签，如 <aurora_time>"},
    }

    dominant = max(scores, key=scores.get) if any(scores.values()) else "plain"
    
    # 模拟快速清洗
    cleaned = raw
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'```[\s\S]*?```', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'</?(?:content|aurora_time|li|aurora)[^>]*>', '', cleaned)
    if dominant == "forum_style":
        cleaned = re.sub(r'^[【\[].*?[】\]].*$', '', cleaned, flags=re.MULTILINE)
    elif dominant == "bold_action":
        cleaned = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'[\1]', cleaned)
    elif dominant == "parenthesis_thought":
        cleaned = re.sub(r'[（(]([^)）]{2,60})[)）]', r'[内心:\1]', cleaned)
    cleaned = re.sub(r'(当前bgm:|⋯♡⋯|𐙚₊˚|☆₊⁺).*?(\n|$)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned).strip()

    clean_rate = round((len(raw) - len(cleaned)) / max(len(raw), 1) * 100, 1)
    
    recs = []
    if dominant == "markdown_noise": recs.append("⚠️ 发现代码块——强烈建议在导入前清除，避免污染向量空间。")
    if clean_rate > 30: recs.append(f"🎯 清洗率 {clean_rate}% 偏高，建议检查 UI 废料比例。")

    return {
        "style": {
            "detected_style": dominant,
            "style_name": style_meta.get(dominant, {}).get("name", "普通纯文本"),
            "confidence_score": scores.get(dominant, 0),
            "description": style_meta.get(dominant, {}).get("desc", ""),
            "all_scores": scores
        },
        "cleaned_preview": cleaned[:800],
        "original_length": len(raw),
        "cleaned_length": len(cleaned),
        "clean_rate_pct": clean_rate,
        "recommendations": recs
    }

# ============================
# API: Standalone Search & Re-ranking
# ============================
@app.get("/api/universe/search")
async def search_universes(query: str, character: str, k: int = 8, human_weight: float = 0.4, target_universes: str = ""):
    try:
        index_pattern = os.path.join(rag_manager.vectorstore_dir, f"{character}*.index")
        index_files = glob.glob(index_pattern)
        
        target_uids = set(target_universes.split(",")) if target_universes else set()
        world_lines = []
        
        for fp in index_files:
            basename = os.path.basename(fp).replace(".index", "")
            wl = basename[len(character):].lstrip("_") if basename != character else None
            
            if target_uids:
                if not wl or not any(tuid == wl or tuid.startswith(wl + "_") for tuid in target_uids):
                    continue
            world_lines.append(wl)
            
        if not world_lines:
            return {"results": [], "message": "No matching indexes found after filtering.", "searched_universes": 0}

        all_docs = []
        async def fetch_vs(wl):
            vs = rag_manager.load_index(character, wl)
            if vs:
                # similarity_search_with_relevance_scores gives tuples of (Document, score)
                scored = rag_manager.search_verse(vs, query, k=k)
                # Map tuple back to doc but embed 'raw_dist'
                ret = []
                for doc, dist in scored:
                    doc.metadata["score"] = dist
                    ret.append(doc)
                return ret
            return []

        tasks = [fetch_vs(wl) for wl in world_lines]
        results = await asyncio.gather(*tasks)
        for r in results:
            all_docs.extend(r)

        # Mock re-ranking calculation (0 to 1 similarity + implicit user feedback weight)
        sim_weight = 1.0 - human_weight
        final_results = []
        seen = set()
        for doc in all_docs:
            if doc.page_content in seen: continue
            seen.add(doc.page_content)
            
            # Simulated human feedback average score: defaults to 3 for unrated
            human_score = 3.0
            similarity = max(0.0, float(doc.metadata.get("score", 1.0)))
            
            final_score = similarity * sim_weight + (human_score / 5.0) * human_weight
            
            final_results.append({
                "chunk_id": doc.metadata.get("chunk_id", "fallback_id"),
                "text": doc.page_content,
                "metadata": doc.metadata,
                "similarity": round(similarity, 3),
                "human_avg_score": human_score,
                "final_score": round(final_score, 3)
            })

        final_results.sort(key=lambda x: x["final_score"], reverse=True)
        return {"results": final_results[:k], "searched_universes": len(world_lines)}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
