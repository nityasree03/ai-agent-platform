import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["AGENT_FORCE_MOCK"] = "1"

from agent.tools.calculator_tool import calculator_tool
from agent.tools.db_query_tool import db_query_tool
from agent.tools.kb_retriever_tool import kb_retriever_tool
from agent.tools.search_tool import web_search_tool
from agent.tools import call_tool
from agent.simple_runner import run_agent


def test_calculator_basic():
    result = calculator_tool("2 + 2")
    assert result["result"] == 4


def test_calculator_rejects_unsafe_input():
    result = calculator_tool("__import__('os').system('echo hi')")
    assert "error" in result


def test_db_query_select_works():
    result = db_query_tool("SELECT * FROM customers")
    assert "rows" in result
    assert len(result["rows"]) == 4


def test_db_query_rejects_writes():
    result = db_query_tool("DROP TABLE customers")
    assert "error" in result


def test_kb_retriever_finds_relevant_doc():
    result = kb_retriever_tool("What is the expense reimbursement policy?")
    assert result["results"]
    assert "Expense" in result["results"][0]["title"]


def test_kb_retriever_no_match():
    result = kb_retriever_tool("xyzzy nonexistent topic qwerty")
    assert result["results"] == []


def test_web_search_mock_mode():
    result = web_search_tool("anything")
    assert result["source"] == "mock"
    assert result["results"]


def test_tool_registry_dispatch():
    result = call_tool("calculator", {"expression": "3*3"})
    assert result["result"] == 9


def test_tool_registry_unknown_tool():
    result = call_tool("not_a_real_tool", {})
    assert "error" in result


def test_agent_loop_sql_path():
    state = run_agent("What were Q2 sales for Widget X?")
    assert state["final_answer"]
    assert state["tool_call_count"] >= 1
    assert "15500" in state["final_answer"] or "Widget X" in state["final_answer"]


def test_agent_loop_calculator_path():
    state = run_agent("Calculate 100 * 2")
    assert "200" in state["final_answer"]


def test_agent_loop_respects_step_budget():
    state = run_agent("What were Q2 sales for Widget X?")
    assert state["steps"] <= 7


def test_self_correction_retries_on_kb_no_match():
    state = run_agent("kb: zzqx flibbertigibbet xenomorph wobblefritz")
    trace = state["trace"]
    tools_called = [s["tool"] for s in trace if s["node"] == "executor"]
    assert "kb_retriever" in tools_called
    assert "web_search" in tools_called
    assert state["self_correction_count"] >= 1

