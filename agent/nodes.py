"""
Node functions for the agent loop.

Each node receives and returns the shared state dict. Plain functions, easy
to unit test in isolation.
"""
from __future__ import annotations

import json
import time

from .llm_client import get_llm_client, BaseLLMClient
from .prompts import PLANNER_SYSTEM_PROMPT, REFLECTOR_SYSTEM_PROMPT
from .tools import call_tool

MAX_STEPS = 6  # hard cap to prevent infinite planner<->tool loops


def _parse_json_response(text: str) -> dict:
    """LLMs occasionally wrap JSON in markdown fences; strip those defensively."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"needs_tool": False, "final_answer": text, "parse_error": True}


def planner_node(state: dict, llm: BaseLLMClient | None = None) -> dict:
    """Decide the next action: call a tool, or produce the final answer."""
    llm = llm or get_llm_client()
    state.setdefault("messages", [])
    state.setdefault("steps", 0)
    state.setdefault("trace", [])

    if state["steps"] >= MAX_STEPS:
        state["needs_tool"] = False
        state["final_answer"] = (
            "I wasn't able to complete this task within the step budget. "
            "Here is my best partial answer based on what was gathered so far."
        )
        state["trace"].append({"node": "planner", "note": "max_steps_reached", "ts": time.time()})
        return state

    start = time.time()
    response = llm.complete(PLANNER_SYSTEM_PROMPT, state["messages"])
    parsed = _parse_json_response(response.text)

    state["needs_tool"] = parsed.get("needs_tool", False)
    state["thought"] = parsed.get("thought", "")
    state["steps"] += 1

    if state["needs_tool"]:
        state["pending_tool"] = parsed.get("tool")
        state["pending_tool_args"] = parsed.get("tool_args", {})
    else:
        state["final_answer"] = parsed.get("final_answer", "")

    state["trace"].append({
        "node": "planner",
        "thought": state["thought"],
        "needs_tool": state["needs_tool"],
        "tool": parsed.get("tool"),
        "latency_s": round(time.time() - start, 3),
        "tokens": response.total_tokens,
        "ts": time.time(),
    })
    state["messages"].append({"role": "assistant", "content": response.text})
    return state


def executor_node(state: dict) -> dict:
    """Execute the tool the planner requested and append the result to history."""
    tool_name = state.get("pending_tool")
    tool_args = state.get("pending_tool_args", {})
    allowed_tools = state.get("allowed_tools")
    if allowed_tools and tool_name not in allowed_tools:
        result = {"error": f"Tool '{tool_name}' is not available to this sub-agent. Allowed: {allowed_tools}"}
        state.setdefault("tool_call_count", 0)
        state["tool_call_count"] += 1
        state["last_tool_result"] = result
        state["last_tool_succeeded"] = False
        state["trace"].append({
            "node": "executor", "tool": tool_name, "args": tool_args,
            "result": result, "succeeded": False, "latency_s": 0.0, "ts": time.time(),
        })
        state["messages"].append({"role": "user", "content": f"tool_result for {tool_name}: {json.dumps(result)}"})
        return state

    start = time.time()
    result = call_tool(tool_name, tool_args)
    latency = round(time.time() - start, 3)

    state.setdefault("tool_call_count", 0)
    state["tool_call_count"] += 1
    state["last_tool_result"] = result
    found_nothing = result.get("results") == []
    state["last_tool_succeeded"] = "error" not in result and not found_nothing

    state["trace"].append({
        "node": "executor",
        "tool": tool_name,
        "args": tool_args,
        "result": result,
        "succeeded": state["last_tool_succeeded"],
        "latency_s": latency,
        "ts": time.time(),
    })
    state["messages"].append({
        "role": "user",
        "content": f"tool_result for {tool_name}: {json.dumps(result)}",
    })
    return state


def reflector_node(state: dict, llm: BaseLLMClient | None = None) -> dict:
    """Judge the latest tool result; decide whether to retry or proceed."""
    llm = llm or get_llm_client()
    start = time.time()
    response = llm.complete(REFLECTOR_SYSTEM_PROMPT, state["messages"])
    parsed = _parse_json_response(response.text)

    task_complete = parsed.get("task_complete", False)
    should_retry = parsed.get("retry", False) and not state["last_tool_succeeded"]

    if should_retry:
        state.setdefault("self_correction_count", 0)
        state["self_correction_count"] += 1

    state["task_complete"] = task_complete

    state["trace"].append({
        "node": "reflector",
        "thought": parsed.get("thought", ""),
        "task_complete": task_complete,
        "retry": should_retry,
        "latency_s": round(time.time() - start, 3),
        "tokens": response.total_tokens,
        "ts": time.time(),
    })
    return state
