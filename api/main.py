"""
FastAPI app exposing the multi-agent platform over HTTP.

Endpoints:
  POST /agent/run            -> run a query, get back the final answer + a trace ID
  GET  /agent/trace/{trace_id} -> retrieve the full step-by-step reasoning for that run
  GET  /health                -> basic liveness check

Run locally:
    uvicorn api.main:app --reload
Then test:
    curl -X POST localhost:8000/agent/run -H "Content-Type: application/json" -d '{"query": "What were Q2 sales for Widget X?"}'
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.multi_agent_runner import run_multi_agent

app = FastAPI(title="AI Agent Platform", version="0.1.0")

# In-memory store mapping trace_id -> full run state. Resets when the
# server restarts; fine for a portfolio demo, swap for Redis/DB in production.
_RUN_STORE: dict[str, dict] = {}


class RunRequest(BaseModel):
    query: str


class RunResponse(BaseModel):
    trace_id: str
    route: str
    final_answer: str
    steps: int
    tool_call_count: int
    self_correction_count: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/run", response_model=RunResponse)
def agent_run(request: RunRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    state = run_multi_agent(request.query)
    trace_id = str(uuid.uuid4())
    _RUN_STORE[trace_id] = state

    return RunResponse(
        trace_id=trace_id,
        route=state.get("route", "unknown"),
        final_answer=state.get("final_answer", ""),
        steps=state.get("steps", 0),
        tool_call_count=state.get("tool_call_count", 0),
        self_correction_count=state.get("self_correction_count", 0),
    )


@app.get("/agent/trace/{trace_id}")
def agent_trace(trace_id: str):
    state = _RUN_STORE.get(trace_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No run found with trace_id '{trace_id}'")
    return {
        "trace_id": trace_id,
        "route": state.get("route"),
        "routing_reason": state.get("routing_reason"),
        "final_answer": state.get("final_answer"),
        "trace": state.get("trace", []),
        "tracing_result": state.get("tracing_result", {}),
    }
