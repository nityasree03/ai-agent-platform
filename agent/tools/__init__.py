"""Tool registry — single place every other module imports tools from."""
from .calculator_tool import calculator_tool, TOOL_SPEC as CALCULATOR_SPEC
from .db_query_tool import db_query_tool, TOOL_SPEC as DB_QUERY_SPEC
from .kb_retriever_tool import kb_retriever_tool, TOOL_SPEC as KB_RETRIEVER_SPEC
from .search_tool import web_search_tool, TOOL_SPEC as WEB_SEARCH_SPEC

TOOL_REGISTRY = {
    "calculator": {"fn": calculator_tool, "spec": CALCULATOR_SPEC},
    "db_query": {"fn": db_query_tool, "spec": DB_QUERY_SPEC},
    "kb_retriever": {"fn": kb_retriever_tool, "spec": KB_RETRIEVER_SPEC},
    "web_search": {"fn": web_search_tool, "spec": WEB_SEARCH_SPEC},
}


def call_tool(name: str, args: dict) -> dict:
    """Dispatch a tool call by name with kwargs. Returns the tool's dict result."""
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool '{name}'. Available: {list(TOOL_REGISTRY)}"}
    try:
        return TOOL_REGISTRY[name]["fn"](**args)
    except TypeError as e:
        return {"error": f"Bad arguments for tool '{name}': {e}"}

