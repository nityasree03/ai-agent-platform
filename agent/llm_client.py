
"""
LLM client abstraction.

Two implementations behind one interface:
  - MockLLMClient:      zero-cost, deterministic, runs the full agent loop
                         end-to-end without any API key.
  - AnthropicLLMClient: real calls to Claude (Haiku by default for cost
                         control). Activates automatically when
                         ANTHROPIC_API_KEY is set in the environment.

Swap clients with one line — see `get_llm_client()` at the bottom.
"""
from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseLLMClient:
    """Common interface every LLM backend must implement."""

    name: str = "base"

    def complete(self, system: str, messages: list[dict[str, str]]) -> LLMResponse:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """
    Deterministic, rule-based stand-in for a real LLM.

    Pattern-matches the latest user/tool message to decide whether to call a
    tool, reflect on a tool result, or produce a final answer. Drives the
    planner -> tool -> reflector graph end-to-end for free, with zero
    network calls.
    """

    name = "mock"

    def complete(self, system: str, messages: list[dict[str, str]]) -> LLMResponse:
        last = messages[-1]["content"] if messages else ""
        joined_history = " ".join(m["content"] for m in messages).lower()

        if "you are the planner" in system.lower():
            text = self._plan(last, joined_history, messages)
        elif "you are the reflector" in system.lower():
            text = self._reflect(last, joined_history)
        elif "you are the supervisor" in system.lower():
            text = self._route(last)
        else:
            text = json.dumps({"final_answer": f"Mock response to: {last[:120]}"})

        approx_tokens = max(1, len(text.split()))
        return LLMResponse(text=text, input_tokens=approx_tokens * 3, output_tokens=approx_tokens)

    def _plan(self, last: str, history: str, messages: list[dict[str, str]]) -> str:
        q = last.lower()

        last_tool_result_msg = next(
            (m["content"] for m in reversed(messages) if m["content"].lower().startswith("tool_result")),
            None,
        )

        if last_tool_result_msg is not None:
            failed = '"error"' in last_tool_result_msg or '"results": []' in last_tool_result_msg
            already_retried = sum(
                1 for m in messages if m["content"].lower().startswith("tool_result")
            ) > 1

            if failed and not already_retried:
                if "db_query" in last_tool_result_msg:
                    sql = self._build_sql_for(history)
                    return json.dumps({
                        "thought": "The previous query wasn't valid SQL. Reformulating as a SELECT statement.",
                        "needs_tool": True,
                        "tool": "db_query",
                        "tool_args": {"query": sql},
                    })
                return json.dumps({
                    "thought": "The previous tool call failed or found nothing. Falling back to a web search.",
                    "needs_tool": True,
                    "tool": "web_search",
                    "tool_args": {"query": messages[0]["content"]},
                })

            return json.dumps({
                "thought": "I have the information needed to answer.",
                "needs_tool": False,
                "final_answer": self._synthesize_answer(last_tool_result_msg),
            })

        original_query = messages[0]["content"].lower() if messages else q

        has_arithmetic_keyword = any(
            k in original_query for k in ["calculate", "sum", "total", "average", "threshold"]
        )
        has_bare_math_expr = bool(re.search(r"\d+\s*[\+\-\*/%]\s*\d+", original_query)) or (
            "%" in original_query and "of" in original_query and re.search(r"\d", original_query)
        )
        mentions_sales_data = any(k in original_query for k in ["sales", "orders", "database"])

        if (has_arithmetic_keyword or has_bare_math_expr) and not mentions_sales_data:
            expr = self._extract_math_expression(original_query)
            return json.dumps({
                "thought": "This requires arithmetic; calling the calculator tool.",
                "needs_tool": True,
                "tool": "calculator",
                "tool_args": {"expression": expr},
            })
        if any(k in original_query for k in [
            "policy", "runbook", "documentation", "docs", "knowledge base", "kb",
            "sla", "escalation", "retention", "reimbursement", "pre-approval", "ticket",
        ]):
            return json.dumps({
                "thought": "This requires looking up internal documentation.",
                "needs_tool": True,
                "tool": "kb_retriever",
                "tool_args": {"query": messages[0]["content"]},
            })
        if any(k in original_query for k in ["search", "look up", "find out", "latest", "news", "trends", "developments", "updates"]):
            return json.dumps({
                "thought": "This requires a web search.",
                "needs_tool": True,
                "tool": "web_search",
                "tool_args": {"query": messages[0]["content"]},
            })
        if any(k in original_query for k in ["sales", "orders", "customer", "revenue", "database", "sql", "q1", "q2", "q3", "q4"]):
            sql = self._build_sql_for(original_query)
            return json.dumps({
                "thought": "This requires querying the sales database.",
                "needs_tool": True,
                "tool": "db_query",
                "tool_args": {"query": sql},
            })

        return json.dumps({
            "thought": "No tool needed; answering directly.",
            "needs_tool": False,
            "final_answer": f"Here's a direct answer based on what I know: {messages[0]['content'][:200]}",
        })

    def _build_sql_for(self, text: str) -> str:
        t = text.lower()
        quarter = next((q for q in ["q1", "q2", "q3", "q4"] if q in t), None)
        product = "Widget X" if "widget x" in t else ("Widget Y" if "widget y" in t else None)

        where_clauses = []
        if quarter:
            where_clauses.append(f"quarter = '{quarter.upper()}'")
        if product:
            where_clauses.append(f"product = '{product}'")

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return f"SELECT product, quarter, SUM(amount) as total_amount FROM orders{where_sql} GROUP BY product, quarter;"
    def _reflect(self, last: str, history: str) -> str:
        failed = "error" in last.lower() or "not found" in last.lower() or '"results": []' in last
        if failed:
            return json.dumps({
                "thought": "The tool call failed or returned nothing useful. Re-planning with a different approach.",
                "task_complete": False,
                "retry": True,
            })
        return json.dumps({
            "thought": "Tool result looks usable. Moving toward a final answer.",
            "task_complete": False,
            "retry": False,
        })

    def _route(self, last: str) -> str:
        q = last.lower()
        if any(k in q for k in ["calculate", "sum", "total", "sql", "database", "sales", "revenue", "threshold"]):
            return json.dumps({"route": "data_agent", "reason": "Task involves computation or structured data lookup."})
        return json.dumps({"route": "research_agent", "reason": "Task involves search or knowledge lookup."})

    def _extract_math_expression(self, q: str) -> str:
        pct_of = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", q)
        if pct_of:
            pct, base = pct_of.groups()
            return f"({pct}/100)*{base}"
        match = re.search(r"[\d\.\s\+\-\*/\(\)%]{3,}", q)
        return match.group(0).strip() if match else "1+1"

    def _synthesize_answer(self, last_tool_result_msg: str) -> str:
        try:
            json_part = last_tool_result_msg.split(":", 1)[1].strip()
            result = json.loads(json_part)
        except Exception:
            return "Based on the tool results above, here is the synthesized final answer."

        if "rows" in result and result["rows"]:
            cols = result.get("columns", [])
            lines = [", ".join(f"{c}={v}" for c, v in zip(cols, row)) for row in result["rows"]]
            return "Based on the database query: " + "; ".join(lines)
        if "result" in result:
            return f"The calculated result is {result['result']}."
        if "results" in result and result["results"]:
            first = result["results"][0]
            if "snippet" in first:
                return f"Based on search results: {first.get('title', '')} — {first['snippet']}"
            if "text" in first:
                return f"Based on internal docs ({first.get('title', '')}): {first['text']}"
        return "I wasn't able to find a usable result, so I'm answering with the best information available."


class AnthropicLLMClient(BaseLLMClient):
    """Real Claude calls. Requires ANTHROPIC_API_KEY in the environment."""

    name = "anthropic"

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "anthropic package not installed. Run: pip3 install anthropic --break-system-packages"
            ) from e
        self._client = anthropic.Anthropic()
        self.model = model

    def complete(self, system: str, messages: list[dict[str, str]]) -> LLMResponse:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )


def get_llm_client() -> BaseLLMClient:
    """
    Single switch point for the whole app.

    - If ANTHROPIC_API_KEY is set -> real Claude Haiku calls.
    - Otherwise -> MockLLMClient (free, deterministic, no network).
    - AGENT_FORCE_MOCK=1 forces mock mode even with a key present.
    """
    if os.environ.get("AGENT_FORCE_MOCK") == "1":
        return MockLLMClient()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicLLMClient()
    return MockLLMClient()
