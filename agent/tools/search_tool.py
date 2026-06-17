"""
Web search tool.

Uses the Tavily API if TAVILY_API_KEY is set (free tier available);
otherwise falls back to a small mock search index so the tool — and the
whole agent graph — still runs with zero external dependencies.
"""
from __future__ import annotations

import os

_MOCK_RESULTS = {
    "default": [
        {
            "title": "Mock Search Result",
            "url": "https://example.com/mock-result",
            "snippet": (
                "This is a placeholder search result. Set TAVILY_API_KEY in your "
                "environment to enable real web search."
            ),
        }
    ]
}


def _mock_search(query: str) -> list[dict]:
    return _MOCK_RESULTS["default"]


def _tavily_search(query: str, api_key: str) -> list[dict]:
    import requests

    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": 5},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in data.get("results", [])
    ]


def web_search_tool(query: str) -> dict:
    """
    Search the web for a query.

    Args:
        query: Search query string.

    Returns:
        {"results": [{"title", "url", "snippet"}, ...]}
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    try:
        results = _tavily_search(query, api_key) if api_key else _mock_search(query)
        return {"results": results, "source": "tavily" if api_key else "mock"}
    except Exception as e:
        return {"error": f"Search failed: {e}"}


TOOL_SPEC = {
    "name": "web_search",
    "description": "Search the web for current information.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."}
        },
        "required": ["query"],
    },
}
