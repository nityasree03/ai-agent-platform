"""
Multi-agent runner — Supervisor routes to Research Agent or Data Agent.

Each sub-agent runs the same planner -> executor -> reflector loop from
Week 1 (agent/nodes.py), but scoped to its own pair of tools via
`allowed_tools` in the shared state. This is what makes it a genuine
multi-agent split rather than just a label: the Data Agent literally
cannot call web_search or kb_retriever, and vice versa.
"""
from __future__ import annotations

from .nodes import planner_node, executor_node, reflector_node, MAX_STEPS
from .supervisor import supervisor_node, SUB_AGENT_TOOLS


def run_multi_agent(user_query: str) -> dict:
    """Run a task through the Supervisor, then the routed sub-agent's loop."""
    state: dict = {
        "messages": [{"role": "user", "content": user_query}],
        "steps": 0,
        "trace": [],
    }

    # Step 1: Supervisor decides which sub-agent handles this task.
    state = supervisor_node(state)
    route = state["route"]
    state["allowed_tools"] = SUB_AGENT_TOOLS[route]

    # Step 2: Run the planner/executor/reflector loop, scoped to that
    # sub-agent's tools only.
    for _ in range(MAX_STEPS + 1):
        state = planner_node(state)
        if not state.get("needs_tool"):
            break
        state = executor_node(state)
        state = reflector_node(state)
        if state.get("task_complete"):
            break

    state.setdefault("final_answer", "No answer produced.")
    return state


if __name__ == "__main__":
    import json
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "What were Q2 sales for Widget X?"
    result = run_multi_agent(query)
    print(json.dumps({
        "route": result.get("route"),
        "routing_reason": result.get("routing_reason"),
        "final_answer": result.get("final_answer"),
        "steps": result.get("steps"),
        "tool_call_count": result.get("tool_call_count", 0),
        "self_correction_count": result.get("self_correction_count", 0),
    }, indent=2))
    print("\n--- trace ---")
    for step in result.get("trace", []):
        print(json.dumps(step, default=str))
