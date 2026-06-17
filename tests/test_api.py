import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["AGENT_FORCE_MOCK"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_agent_run_sql_query():
    response = client.post("/agent/run", json={"query": "What were Q2 sales for Widget X?"})
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "data_agent"
    assert "15500" in data["final_answer"]
    assert "trace_id" in data


def test_agent_run_rejects_empty_query():
    response = client.post("/agent/run", json={"query": "  "})
    assert response.status_code == 400


def test_agent_trace_retrieval():
    run_response = client.post("/agent/run", json={"query": "What is our expense reimbursement policy?"})
    trace_id = run_response.json()["trace_id"]

    trace_response = client.get(f"/agent/trace/{trace_id}")
    assert trace_response.status_code == 200
    data = trace_response.json()
    assert data["trace_id"] == trace_id
    assert len(data["trace"]) > 0
    assert data["route"] == "research_agent"


def test_agent_trace_not_found():
    response = client.get("/agent/trace/nonexistent-id")
    assert response.status_code == 404

