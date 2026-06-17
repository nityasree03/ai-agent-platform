import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["AGENT_FORCE_MOCK"] = "1"

from agent.supervisor import supervisor_node, SUB_AGENT_TOOLS
from agent.multi_agent_runner import run_multi_agent
from agent.nodes import executor_node


def test_supervisor_routes_data_questions_to_data_agent():
    state = {"messages": [{"role": "user", "content": "What were Q2 sales for Widget X?"}]}
    result = supervisor_node(state)
    assert result["route"] == "data_agent"


def test_supervisor_routes_policy_questions_to_research_agent():
    state = {"messages": [{"role": "user", "content": "What is our expense reimbursement policy?"}]}
    result = supervisor_node(state)
    assert result["route"] == "research_agent"


def test_data_agent_cannot_call_research_tools():
    state = {
        "pending_tool": "web_search",
        "pending_tool_args": {"query": "test"},
        "allowed_tools": SUB_AGENT_TOOLS["data_agent"],
        "trace": [],
        "messages": [],
    }
    result = executor_node(state)
    assert result["last_tool_succeeded"] is False
    assert "not available" in result["last_tool_result"]["error"]


def test_research_agent_cannot_call_data_tools():
    state = {
        "pending_tool": "calculator",
        "pending_tool_args": {"expression": "1+1"},
        "allowed_tools": SUB_AGENT_TOOLS["research_agent"],
        "trace": [],
        "messages": [],
    }
    result = executor_node(state)
    assert result["last_tool_succeeded"] is False
    assert "not available" in result["last_tool_result"]["error"]

def test_supervisor_does_not_false_match_database_in_research_query():
    """Regression test: 'vector databases' contains the substring 'database'
    and previously false-matched the data_agent route."""
    state = {"messages": [{"role": "user", "content": "What is the latest news on vector databases?"}]}
    result = supervisor_node(state)
    assert result["route"] == "research_agent"


def test_supervisor_routes_bare_arithmetic_to_data_agent():
    """Regression test: bare math expressions without the word 'calculate'
    previously fell through to research_agent by default."""
    state = {"messages": [{"role": "user", "content": "What is 75 * 4?"}]}
    result = supervisor_node(state)
    assert result["route"] == "data_agent"

def test_multi_agent_sql_path_end_to_end():
    result = run_multi_agent("What were Q2 sales for Widget X?")
    assert result["route"] == "data_agent"
    assert "15500" in result["final_answer"]


def test_multi_agent_kb_path_end_to_end():
    result = run_multi_agent("What is our expense reimbursement policy?")
    assert result["route"] == "research_agent"
    assert "30 days" in result["final_answer"]
