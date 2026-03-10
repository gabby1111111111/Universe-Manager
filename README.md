# 🌌 Aegis-Isle Universe Manager (Standalone)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-orange.svg)](https://github.com/facebookresearch/faiss)

Aegis-Isle Universe Manager 是一款专为 **SillyTavern 长时角色扮演生态** 打造的 RAG (Retrieval-Augmented Generation) 独立诊断看板与意图重排工具。

当角色的“剧情副本次数”（Worldlines / Universes）呈指数级增长时，底层的碎片化记忆搜索往往会遇到两大痛点：
1. **输入意图宽泛导致召回精准率下降** (Intent Ambiguity)
2. **重度自定义的 RP 排版风格污染向量库** (Markdown / HTML Noise Pollution)

该工具作为 Aegis-Isle 主生态的外挂式 Dashboard，完美解决了在庞大历史数据中进行多路并发检索、意图提取以及数据清洗的问题。

---

## 🔥 核心特性 (Features)

### 1. 🔍 Cross-Universe Semantic Search & Re-ranking （跨宇宙语义搜索验证与重排）
* **并发多路召回 (Parallel FAISS Retrieval)：** 底层挂载海量独立向量库（如 `12岁_养父_真实开局_xxxx.index` 等角色副本片段）。面对上百个平行宇宙时，可通过筛选指定的“世界线文件ID”或者全库通搜，毫秒级召回目标剧情。
* **基于意图快捷种子的高效匹配 (Intent Query Enhancement)：** 很多时候人类偏向基于口语化的模糊问法。系统通过前置提取种子词意图（如 *回忆型: "你还记得"*, *细节型: "当时发生了什么"*），直接辅助并改写 Query，缩小大模型理解歧义。
* **人机协作排序 (Human-in-the-loop Re-ranking)：** 最终呈现的结果不单纯依靠 L2/Cosine 空间距离。我们独创了允许用户在主应用内提交点赞/踩的评分体系；在此 Dashboard 中，召回结果得分基于 `Final Score = Vector Similarity * (1 - ω) + Human Feedback * ω` 进行混合重排。`ω` (即人类权重) 可以被用户实时调参以测试不同推荐策略的效果。

### 2. 🧹 Data Cleaning & Pre-processing Diagnostic （数据探针与结构化清洗）
* 由于前端 AI 角色引擎往往承载着繁重的格式要求（如 *动作与旁白包边*，`【剧场体标签】`，甚至是直接返回携带属性或样式的 `<aurora_time>`，```` ```html ````），若把这些字符灌进 Embedding 模型，会导致语料被噪声淹没（Noise Overload）。
* **自动化探针侦测：** 开启一键侦测模式，后台利用正则特征矩阵与置信度算法，一秒识别原段落属于 *日式对白体*、*论坛体*，抑或是含有前端渲染废料的结构文本。
* **高纯度萃取率对比：** 提取文本并返回 **“实时清洗率 (Clean Rate) ”** 与纯净切片预览。协助开发者诊断 Embedding 进水现象，保持极高的信息熵。

---

## 🛠 架构设计 (Architecture)

采用完全前后端分离的无状态微服务结构：
- **AI 代理与路由层 (`app.py / core_rag.py`)：** 使用 FastAPI 托管检索服务。仅剥离必要的 langchain-community 和 HuggingFace BGE 模型层实现极轻量部署。
- **视图层 (`dashboard.py`)：** Streamlit 交互面板，将深层的 RAG 参数调整用零代码的方式直观可视化。
- **插拔式数据挂载：** 默认通过 `.env` 中的 `AEGIS_DATA_PATH` 直接挂载 Aegis-Isle 集群产生的原始 `chunks/`, `universes/` 与 `vectorstore/`。

---

## 🚀 快速启动指南

### 1. 安装依赖
此项目支持独立运行。确保你已有 Python 环境，并安装了依赖项：

```bash
pip install -r requirements.txt
```

### 2. 配置数据源挂载点
复制环境变量示例文件：
```bash
cp .env.example .env
```
并编辑 `.env` 文件，将 `AEGIS_DATA_PATH` 指向你机器上 `Aegis-Isle` 系统的 `/data` 目录绝对路径，使其共享底层记忆资源库。

### 3. 分别启动后端和看板
打开终端一，启动核心检索 API（基于 Uvicorn）：
```bash
python api_app.py
```
> 服务器此时监听在 `http://127.0.0.1:8001`

打开另一个终端二，启动可视化工具面板：
```bash
streamlit run dashboard.py
```
> 此时你的浏览器将自动弹出本地看板主页，尽情探索 RAG 性能的边界吧！

---
*Created as part of the Aegis-Isle project ecosystem for scalable RP memory management.*
