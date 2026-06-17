"""
Supervisor node — routes an incoming task to one of two sub-agents.

- Research Agent: handles web_search and kb_retriever tasks.
- Data Agent: handles calculator and db_query tasks.

The supervisor itself uses the same LLM client as the planner/reflector
(mock by default, real Claude Haiku if ANTHROPIC_API_KEY is set), via the
SUPERVISOR_SYSTEM_PROMPT already defined in agent/prompts.py.
"""
from __future__ import annotations

import json
import time

from .llm_client import get_llm_client, BaseLLMClient
from .prompts import SUPERVISOR_SYSTEM_PROMPT

# Which tools belong to which sub-agent. Used to scope each sub-agent's
# planner so it only ever calls tools in its own lane.
SUB_AGENT_TOOLS = {
    "research_agent": ["web_search", "kb_retriever"],
    "data_agent": ["calculator", "db_query"],
}


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"route": "research_agent", "reason": "Could not parse routing decision; defaulting.", "parse_error": True}


def supervisor_node(state: dict, llm: BaseLLMClient | None = None) -> dict:
    """Classify the task and decide which sub-agent should handle it."""
    llm = llm or get_llm_client()
    start = time.time()

    user_query = state["messages"][0]["content"]
    response = llm.complete(SUPERVISOR_SYSTEM_PROMPT, [{"role": "user", "content": user_query}])
    parsed = _parse_json_response(response.text)

    route = parsed.get("route", "research_agent")
    if route not in SUB_AGENT_TOOLS:
        route = "research_agent"

    state["route"] = route
    state["routing_reason"] = parsed.get("reason", "")
    state.setdefault("trace", [])
    state["trace"].append({
        "node": "supervisor",
        "route": route,
        "reason": state["routing_reason"],
        "latency_s": round(time.time() - start, 3),
        "tokens": response.total_tokens,
        "ts": time.time(),
    })
    return state
