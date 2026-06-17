"""
Streamlit UI for the AI Agent Platform.

A chat panel for asking questions, plus a live reasoning-trace viewer
showing each step: supervisor routing -> planner thought -> tool call ->
tool result -> reflector judgment -> final answer.

Run locally:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from agent.multi_agent_runner import run_multi_agent

st.set_page_config(page_title="AI Agent Platform", layout="wide")

st.title("AI Agent Platform")
st.caption("Multi-agent system: Supervisor routes to a Research Agent (search + knowledge base) or a Data Agent (calculator + SQL).")

if "history" not in st.session_state:
    st.session_state.history = []

chat_col, trace_col = st.columns([1, 1])

with chat_col:
    st.subheader("Chat")
    query = st.text_input("Ask a question", placeholder="e.g. What were Q2 sales for Widget X?")
    run_clicked = st.button("Run", type="primary")

    if run_clicked and query.strip():
        with st.spinner("Running agent..."):
            result = run_multi_agent(query)
        st.session_state.history.append({"query": query, "result": result})

    if st.session_state.history:
        latest = st.session_state.history[-1]
        st.markdown(f"**You:** {latest['query']}")
        st.markdown(f"**Agent ({latest['result'].get('route', 'unknown')}):** {latest['result'].get('final_answer', '')}")

        st.divider()
        st.caption("Previous turns")
        for turn in reversed(st.session_state.history[:-1]):
            with st.expander(turn["query"]):
                st.write(turn["result"].get("final_answer", ""))

with trace_col:
    st.subheader("Reasoning Trace")
    if st.session_state.history:
        latest = st.session_state.history[-1]["result"]
        st.markdown(f"**Route:** `{latest.get('route', 'unknown')}` — {latest.get('routing_reason', '')}")
        st.markdown(f"**Steps:** {latest.get('steps', 0)} &nbsp;|&nbsp; **Tool calls:** {latest.get('tool_call_count', 0)} &nbsp;|&nbsp; **Self-corrections:** {latest.get('self_correction_count', 0)}")
        st.divider()

        for step in latest.get("trace", []):
            node = step.get("node", "unknown")
            if node == "supervisor":
                st.info(f"**Supervisor** routed to `{step.get('route')}` — {step.get('reason', '')}")
            elif node == "planner":
                tool = step.get("tool")
                if tool:
                    st.write(f"**Planner:** {step.get('thought', '')} → calling `{tool}`")
                else:
                    st.write(f"**Planner:** {step.get('thought', '')}")
            elif node == "executor":
                with st.expander(f"**Executor:** called `{step.get('tool')}`  ({'✓ succeeded' if step.get('succeeded') else '✗ failed'})"):
                    st.json(step.get("result", {}))
            elif node == "reflector":
                icon = "🔁" if step.get("retry") else "✓"
                st.write(f"**Reflector** {icon}: {step.get('thought', '')}")

        tracing_result = latest.get("tracing_result", {})
        st.divider()
        if tracing_result.get("langsmith_logged"):
            st.success(f"Logged to LangSmith (project: {tracing_result.get('project')})")
        else:
            st.caption(f"LangSmith: {tracing_result.get('reason', 'not configured')}")
    else:
        st.caption("Run a query to see the reasoning trace here.")
