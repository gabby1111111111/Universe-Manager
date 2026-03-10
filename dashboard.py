import streamlit as st
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8001/api")

st.set_page_config(page_title="RAG Universe Explorer", page_icon="🌌", layout="wide")

def api_get(path: str, **kwargs):
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=60, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_post(path: str, json_data: dict, **kwargs):
    try:
        r = httpx.post(f"{API_BASE}{path}", json=json_data, timeout=60, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

st.title("🌌 Aegis-Isle Universe Explorer (Standalone)")
st.caption("独立展示版 RAG 检索诊断工具（需挂载底层数据文件夹）")

tab_search, tab_clean = st.tabs(["🔍 语义搜索与意图排序", "🧹 预设风格清洗探针"])

# ================================
# TAB 1: SEARCH & RE-RANKING
# ================================
with tab_search:
    st.markdown("### 🔍 跨记忆分形 (Worldlines) 搜索")
    colA, colB = st.columns([1, 1])
    character = colA.text_input("角色名", value="邹峥", help="FAISS 索引前缀名")
    target_unvs = colB.text_input("限定文件后缀（逗号分隔，可选）", value="12岁_养父_真实开局")
    
    # 意图种子词
    seed_data = api_get("/universe/query_seed_phrases")
    if seed_data and "categories" in seed_data:
        st.markdown("**💭 快捷意图种子词**")
        prefix = ""
        for cat_name, phrases in seed_data["categories"].items():
            with st.expander(f"**{cat_name}**", expanded=(cat_name == "回忆型")):
                cols_p = st.columns(min(len(phrases), 4))
                for pi, phrase in enumerate(phrases):
                    if cols_p[pi % 4].button(phrase, key=f"seed_{cat_name}_{pi}"):
                        st.session_state.query_prefix = phrase
                        
    prefix = st.session_state.get("query_prefix", "")
    query = st.text_input("搜索内容 (Query)", value=prefix)
    
    col_s1, col_s2 = st.columns([1, 2])
    k_num = col_s1.number_input("Top K 条数", min_value=1, max_value=20, value=8)
    hw_pct = col_s2.slider("意图反馈偏好权重 % (Re-ranking Weight)", 0, 100, 40)
    
    if st.button("开始向量检索", type="primary") and query:
        with st.spinner("多路并发向量计算，自动重排序中..."):
            hw = hw_pct / 100.0
            search_url = f"/universe/search?query={query}&character={character}&k={k_num}&human_weight={hw}"
            if target_unvs:
                search_url += f"&target_universes={target_unvs}"
            
            res = api_get(search_url)
            
        if res:
            results = res.get("results", [])
            s_count = res.get("searched_universes", 0)
            if results:
                st.success(f"跨 **{s_count}** 个并行宇宙，召回 Top {len(results)}.")
                for idx, r in enumerate(results):
                    st.markdown(f"**#{idx+1} [分数: {r.get('final_score')}]** (VS: {r.get('similarity')}, HR: {r.get('human_avg_score')})")
                    st.info(r['text'])
            else:
                st.warning("未检索到符合条件的上下文切片。")

# ================================
# TAB 2: DATA DIAGNOSTIC
# ================================
with tab_clean:
    st.markdown("### 🧹 ST 预设格式自动化探针")
    st.caption("针对 SillyTavern 内高度自定义的预设格式（例如【事件体】、*旁白体*、```html 渲染层...），判断并展示清洗率，降低向量污染。")
    raw_input = st.text_area(
        "📌 粘贴需要探测的原始 ST 对话格式", height=200,
        value="【小剧场事件】\n*他推了推金丝眼镜。*\n「那件事，你还记得吗？」\n```html\n<div class='thought'>...</div>\n```"
    )
    if st.button("执行诊断与清洗", use_container_width=True, type="primary"):
        with st.spinner("Pipeline 执行中..."):
            res = api_post("/universe/diagnose_clean", {"raw_text": raw_input})
            if res:
                style = res.get("style", {})
                
                c1, c2, c3 = st.columns(3)
                c1.metric("🎨 识别预设格式", style.get('style_name', '未知'))
                c2.metric("🔥 格式噪声清洗率", f"{res.get('clean_rate_pct', 0)}%")
                c3.metric("✅ 模式匹配置信度", style.get('confidence_score', 0))
                
                st.markdown("---")
                for rec in res.get("recommendations", []):
                    st.info(rec)
                    
                cb1, cb2 = st.columns(2)
                cb1.caption("原始数据")
                cb1.code(raw_input, language="markdown")
                cb2.caption("入库前高纯度向量切片")
                cb2.code(res.get('cleaned_preview'), language="markdown")
