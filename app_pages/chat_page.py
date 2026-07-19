"""科研论文问答对话页面 — 流式输出 + 工具面板 + 记忆管理"""
import streamlit as st
from agent.react_agent import ReactAgent


def _render_tool_expander(name: str, content: str, query: str = "", elapsed: float = 0,
                          meta: dict | None = None):
    """根据工具名称渲染结构化折叠面板"""
    label = f"工具: {name}"
    if elapsed:
        label += f" ({elapsed:.1f}s)"

    with st.expander(label, expanded=False):
        if query:
            st.caption(f"检索词: {query}")

        if meta:
            _render_meta(name, meta)

        if content:
            st.text(content[:500])


def _render_meta(name: str, meta: dict):
    """按工具类型渲染 meta 字段"""
    if name in ("academic_search",):
        # 本地检索 → chunk 来源列表
        sources = meta.get("sources", [])
        count = meta.get("count", 0)
        if count:
            st.caption(f"结果数: {count}")
        if sources:
            st.caption("来源:")
            for src in sources[:5]:
                title = src.get("title", "?")
                section = src.get("section", "?")
                page = src.get("page", "?")
                preview = src.get("preview", "")[:60]
                st.text(f"  · 《{title}》| {section} | p.{page}")
                if preview:
                    st.text(f"    {preview}...")

    elif name in ("search_academic_papers",):
        # 在线检索 → 论文元数据列表
        papers = meta.get("papers", [])
        if papers:
            st.caption(f"论文数: {len(papers)}")
            for p in papers:
                authors = ", ".join(p.get("authors", []))
                year = p.get("year", "")
                source = p.get("source", "")
                score = p.get("score", 0)
                abstract = p.get("abstract", "")[:120]
                st.text(f"  · {p.get('title', '?')}")
                st.text(f"    作者: {authors} | {year} | {source} | 分数: {score}")
                if abstract:
                    st.text(f"    摘要: {abstract}...")
        else:
            st.caption("无匹配论文（全部低于阈值）")

    elif name == "kb_missing_abstract":
        # kb_missing 预存元数据
        if meta.get("authors"):
            st.caption(f"作者: {', '.join(meta['authors'][:5])}")
        if meta.get("year"):
            st.caption(f"年份: {meta['year']}")
        if meta.get("venue"):
            st.caption(f"发表: {meta['venue']}")
        if meta.get("doi"):
            st.caption(f"DOI: {meta['doi']}")
        if meta.get("url"):
            st.caption(f"链接: {meta['url']}")

    elif name == "compare_papers":
        titles = meta.get("titles", [])
        if titles:
            st.caption(f"对比论文: {'; '.join(titles)}")


def render_chat_page():
    # --- Session state init ---
    if "agent" not in st.session_state:
        st.session_state.agent = ReactAgent()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "tool_history" not in st.session_state:
        st.session_state.tool_history = []

    # --- Sidebar ---
    with st.sidebar:
        st.header("会话状态")

        mem = st.session_state.agent.memory
        turn_count = mem.turn_count()
        st.caption(f"当前会话轮次: {turn_count}")

        if turn_count > 0:
            with st.expander("短期记忆 (最近4轮)", expanded=False):
                for msg in mem.get_recent_turns()[-8:]:
                    role = "用户" if msg["role"] == "user" else "助手"
                    st.text(f"[{role}] {msg['content'][:50]}...")

        # 长期事实
        facts = st.session_state.agent.fact_store.get_facts_text()
        if facts:
            with st.expander("长期事实", expanded=False):
                st.text(facts[:500])

        # 摘要
        summary_msg = st.session_state.agent.summary.get_summary_message()
        if summary_msg:
            with st.expander("累积摘要", expanded=False):
                st.text(summary_msg["content"][:300])

        with st.expander("工具调用记录", expanded=False):
            for entry in st.session_state.tool_history[-10:]:
                label = entry.get("name", "?")
                if entry.get("query"):
                    label += f" | {entry['query'][:40]}"
                if entry.get("elapsed"):
                    label += f" | {entry['elapsed']:.1f}s"
                st.text(f"{label}")
                if entry.get("content"):
                    st.text(f"  {entry['content'][:100]}...")

        if st.button("清空对话历史"):
            st.session_state.messages = []
            st.session_state.tool_history = []
            st.rerun()

    # --- Main chat area ---
    st.title("科研论文问答系统")
    st.caption("多意图 Agent · 本地知识库 + 在线学术检索")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("type") == "tool":
                _render_tool_expander(
                    name=msg.get("name", "unknown"),
                    content=msg.get("content", ""),
                    query=msg.get("query", ""),
                    elapsed=msg.get("elapsed", 0),
                    meta=msg.get("meta"),
                )
            elif msg.get("type") == "references":
                with st.expander("引用来源", expanded=False):
                    st.text(msg["content"])
            else:
                st.markdown(msg["content"])

    # Chat input
    prompt = st.chat_input("请输入你的科研问题...")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})

        with st.chat_message("assistant"):
            text_placeholder = st.empty()
            tool_placeholder = st.empty()
            collected_text: list[str] = []

            for chunk in st.session_state.agent.execute_stream(prompt):
                chunk_type = chunk.get("type", "text")

                if chunk_type == "intent":
                    with st.sidebar:
                        st.caption(f"意图: {chunk['content']}")

                elif chunk_type == "text":
                    collected_text.append(chunk["content"])
                    text_placeholder.markdown("".join(collected_text) + "▌")

                elif chunk_type == "references":
                    ref_content = chunk.get("content", "")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ref_content,
                        "type": "references",
                    })
                    with tool_placeholder.container():
                        with st.expander("引用来源", expanded=False):
                            st.text(ref_content)

                elif chunk_type == "tool":
                    tool_name = chunk.get("name", "unknown")
                    tool_content = chunk.get("content", "")
                    tool_query = chunk.get("query", "")
                    tool_elapsed = chunk.get("elapsed", 0)
                    tool_meta = chunk.get("meta")

                    st.session_state.tool_history.append({
                        "name": tool_name,
                        "content": tool_content,
                        "query": tool_query,
                        "elapsed": tool_elapsed,
                        "meta": tool_meta,
                    })

                    with tool_placeholder.container():
                        _render_tool_expander(
                            name=tool_name, content=tool_content,
                            query=tool_query, elapsed=tool_elapsed, meta=tool_meta,
                        )

                elif chunk_type == "system":
                    if chunk.get("content"):
                        st.caption(chunk["content"])

            # Remove cursor
            final_text = "".join(collected_text)
            text_placeholder.markdown(final_text)

            st.session_state.messages.append({
                "role": "assistant",
                "content": final_text,
                "type": "text",
            })

        st.rerun()
