import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["AGENT_FORCE_MOCK"] = "1"

from agent.tracing import maybe_log_run
from agent.multi_agent_runner import run_multi_agent


def test_tracing_noop_without_langsmith_key():
    """Without LANGSMITH_API_KEY set, tracing should cleanly skip, not error."""
    os.environ.pop("LANGSMITH_API_KEY", None)
    result = maybe_log_run("test query", {"final_answer": "test", "trace": []})
    assert result["langsmith_logged"] is False
    assert "not set" in result["reason"]


def test_multi_agent_run_includes_tracing_result():
    """Every run through run_multi_agent should attach a tracing_result,
    so the eval harness and UI can surface tracing status."""
    state = run_multi_agent("What were Q2 sales for Widget X?")
    assert "tracing_result" in state
    assert "langsmith_logged" in state["tracing_result"]
