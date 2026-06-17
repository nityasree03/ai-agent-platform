"""Calculator tool — safe arithmetic evaluation, no eval() of arbitrary code."""
from __future__ import annotations

import ast
import operator as op

_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def calculator_tool(expression: str) -> dict:
    """
    Evaluate a basic arithmetic expression safely.

    Args:
        expression: e.g. "1500 * 0.9" or "(200 + 50) / 2"

    Returns:
        {"result": float} on success, {"error": str} on failure.
    """
    try:
        cleaned = expression.replace("%", "/100").rstrip("=").strip()
        tree = ast.parse(cleaned, mode="eval")
        result = _safe_eval(tree.body)
        return {"result": result, "expression": cleaned}
    except Exception as e:
        return {"error": f"Could not evaluate expression '{expression}': {e}"}


TOOL_SPEC = {
    "name": "calculator",
    "description": "Evaluate an arithmetic expression and return the numeric result.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Arithmetic expression, e.g. '1500 * 0.9'"}
        },
        "required": ["expression"],
    },
}


