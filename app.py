"""科研论文问答系统 — 基于 LangChain ReAct Agent + RAG 检索增强"""
import streamlit as st

st.set_page_config(page_title="科研论文问答系统", page_icon="📄", layout="wide")

pages = {
    "对话": "app_pages.chat_page",
    "关于": None,
}

with st.sidebar:
    st.title("导航")
    page = st.radio("选择页面", list(pages.keys()), label_visibility="collapsed")

if page == "对话":
    from app_pages.chat_page import render_chat_page
    render_chat_page()
elif page == "关于":
    st.title("关于")
    st.markdown("基于 LangChain ReAct Agent + RAG 检索增强的科研论文智能问答系统")
    st.markdown("### 功能")
    st.markdown("- **普通问答**：针对特定论文/方法/概念的具体问题")
    st.markdown("- **对比分析**：比较多个方法/模型/论文的异同、优劣")
    st.markdown("- **文献综述**：全面了解某个研究领域的发展脉络")
    st.markdown("### 技术栈")
    st.markdown("LangChain + LangGraph + Chroma + Streamlit + SiliconFlow API")
    st.markdown("### 工具集")
    st.markdown("| 工具 | 类型 | 功能 |")
    st.markdown("|------|------|------|")
    st.markdown("| academic_search | 本地 | Chroma + BM25 + Reranker 全文检索 |")
    st.markdown("| search_academic_papers | 在线 | 多源学术数据库检索 |")
    st.markdown("| fetch_paper_metadata | 在线 | 精确标题获取论文元数据 |")
    st.markdown("| fetch_citation_info | 在线 | 精确标题获取引用计数 |")
    st.markdown("| compare_papers | 聚合 | 多篇论文并行对比分析 |")
    st.markdown("| mark_paper_not_in_kb | 持久 | 标记本地知识库缺失论文 |")
    st.markdown("| start_literature_review | 模式 | 触发文献综述模式 |")
