"""
Runner for the planner -> executor -> reflector loop.

This drives the agent end-to-end using plain Python (no external graph
framework required). Each cycle: planner decides the next action, executor
runs it if a tool was requested, reflector judges the result, and the loop
either continues or stops.
"""
from __future__ import annotations

from .nodes import planner_node, executor_node, reflector_node, MAX_STEPS


def run_agent(user_query: str) -> dict:
    """Run a single task through the planner/executor/reflector loop."""
    state: dict = {
        "messages": [{"role": "user", "content": user_query}],
        "steps": 0,
        "trace": [],
    }

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
    result = run_agent(query)
    print(json.dumps({
        "final_answer": result.get("final_answer"),
        "steps": result.get("steps"),
        "tool_call_count": result.get("tool_call_count", 0),
        "self_correction_count": result.get("self_correction_count", 0),
    }, indent=2))
    print("\n--- trace ---")
    for step in result.get("trace", []):
        print(json.dumps(step, default=str))
