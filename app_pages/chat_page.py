"""科研论文问答对话页面 — 流式输出 + 工具面板 + 记忆管理"""
import streamlit as st
from agent.react_agent import ReactAgent


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
                st.text(f"{entry['name']}: {entry['content'][:80]}...")

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
                with st.expander(f"工具: {msg.get('name', 'unknown')}", expanded=False):
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

                elif chunk_type == "tool":
                    tool_name = chunk.get("name", "unknown")
                    tool_content = chunk.get("content", "")

                    st.session_state.tool_history.append({
                        "name": tool_name,
                        "content": tool_content[:200],
                    })

                    with tool_placeholder.container():
                        with st.expander(f"工具: {tool_name}", expanded=False):
                            st.text(tool_content[:500])

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
