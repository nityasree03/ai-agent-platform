"""
LangSmith tracing integration.

Wraps the existing local `trace` list (already populated by every node)
and additionally sends each run to LangSmith if LANGSMITH_API_KEY is set.
If no key is present, this module is a no-op — the local trace still works
exactly as it did in Weeks 1 and 2, so nothing breaks without a key.

Usage:
    from agent.tracing import maybe_log_run
    maybe_log_run(user_query, state)   # call after a run completes
"""
from __future__ import annotations

import os


def _langsmith_enabled() -> bool:
    return bool(os.environ.get("LANGSMITH_API_KEY"))


def maybe_log_run(user_query: str, state: dict) -> dict:
    """
    If LangSmith is configured, log this completed run as a trace.
    Always returns a dict describing what happened (logged, skipped, or
    errored), so callers can surface this in the eval report or UI.
    """
    if not _langsmith_enabled():
        return {"langsmith_logged": False, "reason": "LANGSMITH_API_KEY not set; using local trace only."}

    try:
        from langsmith import Client

        client = Client()
        project = os.environ.get("LANGSMITH_PROJECT", "ai-agent-platform")

        run = client.create_run(
            name="agent_run",
            run_type="chain",
            inputs={"query": user_query},
            outputs={"final_answer": state.get("final_answer", "")},
            project_name=project,
        )
        # Log each node transition as a child run for full step-by-step visibility.
        for step in state.get("trace", []):
            client.create_run(
                name=step.get("node", "unknown_node"),
                run_type="tool" if step.get("node") == "executor" else "chain",
                inputs={"args": step.get("args", {})} if "args" in step else {},
                outputs={k: v for k, v in step.items() if k not in ("node",)},
                project_name=project,
                parent_run_id=run.id if hasattr(run, "id") else None,
            )
        return {"langsmith_logged": True, "project": project}
    except ImportError:
        return {"langsmith_logged": False, "reason": "langsmith package not installed. Run: pip3 install langsmith --break-system-packages"}
    except Exception as e:
        return {"langsmith_logged": False, "reason": f"LangSmith logging failed: {e}"}
