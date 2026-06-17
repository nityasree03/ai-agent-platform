# AI Agent Platform — Multi-Tool Agentic Workflow

A multi-agent system that plans, routes, calls tools, and self-corrects — built around a Supervisor + Research/Data sub-agent architecture, with a planner → executor → reflector loop inside each sub-agent.

## Status: complete

- **Week 1** — Core agent loop, 4 tools, mock LLM client, tests, eval harness (100% success)
- **Week 2** — Supervisor + Research/Data sub-agents with real tool-scoping enforcement, multi-agent eval (100% success, 100% routing accuracy)
- **Week 3** — LangSmith tracing (graceful no-op without a key), hardened eval
- **Week 4** — FastAPI endpoints, Streamlit UI with reasoning-trace viewer, Docker, GitHub Actions CI gate

## Architecture
User query

│

▼

┌────────────┐

│ Supervisor │  classifies the task, routes to a sub-agent

└────────────┘

│

├──► Research Agent (web_search, kb_retriever)

└──► Data Agent (calculator, db_query)

│

▼

┌─────────┐   needs_tool   ┌──────────┐   always   ┌────────────┐

│ Planner │ ─────────────► │ Executor │ ──────────► │ Reflector  │

└─────────┘                └──────────┘             └────────────┘

▲                                                    │

└──────────────── task not complete, loop back ──────┘

Each sub-agent can **only** call its own tools — this is enforced in code (`agent/nodes.py`), not just by convention, and is covered by dedicated tests.

## Quickstart

```bash
pip install -r requirements.txt --break-system-packages

# Run a single query through the full multi-agent pipeline
python -m agent.multi_agent_runner "What were Q2 sales for Widget X?"

# Run the test suite (28 tests)
pytest tests/ -v

# Run the 30-scenario multi-agent evaluation
python eval/run_multi_agent_eval.py

# Start the API
uvicorn api.main:app --reload
# Interactive docs at http://127.0.0.1:8000/docs

# Start the Streamlit UI (separate terminal)
streamlit run app/streamlit_app.py
```

## Docker

```bash
docker build -f docker/Dockerfile -t ai-agent-platform-api .
docker run -d -p 8000:8000 -e AGENT_FORCE_MOCK=1 --name agent-api ai-agent-platform-api
curl http://127.0.0.1:8000/health
```

Or run both services together with docker-compose from the `docker/` directory.

## LLM backend — runs free by default

Set nothing and the whole system runs on a deterministic, zero-cost mock LLM client. Set `ANTHROPIC_API_KEY` and it switches to real Claude Haiku calls automatically, no code changes needed.

## Known limitation

The mock LLM client (`agent/llm_client.py`) is rule-based, not a real language model — it recognizes symbolic math (`20 + 30`) and explicit keywords ("calculate", "policy", "database") but does not parse spelled-out arithmetic ("twenty plus thirty") or open-ended natural language the way a real LLM would. This only affects mock mode; real Claude Haiku calls (with `ANTHROPIC_API_KEY` set) handle natural language correctly.

## Evaluation results

30-scenario eval, multi-agent pipeline: 100% task success rate, 100% routing accuracy, 100% tool-call accuracy, 2.0 average steps to completion.

## Tools

| Tool | Sub-agent | Purpose |
|---|---|---|
| `calculator` | Data Agent | Safe AST-based arithmetic, no `eval()` |
| `db_query` | Data Agent | Read-only SQL over a sample orders/customers SQLite DB |
| `kb_retriever` | Research Agent | Keyword-overlap search over internal policy/runbook docs |
| `web_search` | Research Agent | Tavily API if `TAVILY_API_KEY` set, else mock results |

## Project structure
ai-agent-platform/

├── agent/

│   ├── multi_agent_runner.py   # Supervisor + sub-agent orchestration

│   ├── supervisor.py            # routing logic

│   ├── nodes.py                  # planner, executor, reflector (shared)

│   ├── llm_client.py             # Mock + Anthropic backends

│   ├── tracing.py                # LangSmith integration

│   ├── simple_runner.py          # single-agent loop (Week 1)

│   ├── graph.py                  # real LangGraph wiring

│   └── tools/

├── api/main.py                   # FastAPI app

├── app/streamlit_app.py          # Streamlit UI

├── eval/                         # eval datasets + harnesses

├── tests/                        # 28 tests across all components

├── docker/                       # Dockerfiles + compose

└── .github/workflows/ci.yml      # CI: tests + eval regression gate

Save: Control + O, Enter, Control + X.
Then let's stage and commit everything:
bashgit add .
git status
Paste back the output.Each sub-agent can **only** call its own tools — this is enforced in code (`agent/nodes.py`), not just by convention, and is covered by dedicated tests.

## Quickstart

```bash
pip install -r requirements.txt --break-system-packages

# Run a single query through the full multi-agent pipeline
python -m agent.multi_agent_runner "What were Q2 sales for Widget X?"

# Run the test suite (28 tests)
pytest tests/ -v

# Run the 30-scenario multi-agent evaluation
python eval/run_multi_agent_eval.py

# Start the API
uvicorn api.main:app --reload
# Interactive docs at http://127.0.0.1:8000/docs

# Start the Streamlit UI (separate terminal)
streamlit run app/streamlit_app.py
```

## Docker

```bash
docker build -f docker/Dockerfile -t ai-agent-platform-api .
docker run -d -p 8000:8000 -e AGENT_FORCE_MOCK=1 --name agent-api ai-agent-platform-api
curl http://127.0.0.1:8000/health
```

Or run both services together with docker-compose from the `docker/` directory.

## LLM backend — runs free by default

Set nothing and the whole system runs on a deterministic, zero-cost mock LLM client. Set `ANTHROPIC_API_KEY` and it switches to real Claude Haiku calls automatically, no code changes needed.

## Known limitation

The mock LLM client (`agent/llm_client.py`) is rule-based, not a real language model — it recognizes symbolic math (`20 + 30`) and explicit keywords ("calculate", "policy", "database") but does not parse spelled-out arithmetic ("twenty plus thirty") or open-ended natural language the way a real LLM would. This only affects mock mode; real Claude Haiku calls (with `ANTHROPIC_API_KEY` set) handle natural language correctly.

## Evaluation results

30-scenario eval, multi-agent pipeline: 100% task success rate, 100% routing accuracy, 100% tool-call accuracy, 2.0 average steps to completion.

## Tools

| Tool | Sub-agent | Purpose |
|---|---|---|
| `calculator` | Data Agent | Safe AST-based arithmetic, no `eval()` |
| `db_query` | Data Agent | Read-only SQL over a sample orders/customers SQLite DB |
| `kb_retriever` | Research Agent | Keyword-overlap search over internal policy/runbook docs |
| `web_search` | Research Agent | Tavily API if `TAVILY_API_KEY` set, else mock results |

## Project structureai-agent-platform/

├── agent/

│   ├── multi_agent_runner.py   # Supervisor + sub-agent orchestration

│   ├── supervisor.py            # routing logic

│   ├── nodes.py                  # planner, executor, reflector (shared)

│   ├── llm_client.py             # Mock + Anthropic backends

│   ├── tracing.py                # LangSmith integration

│   ├── simple_runner.py          # single-agent loop (Week 1)

│   ├── graph.py                  # real LangGraph wiring

│   └── tools/

├── api/main.py                   # FastAPI app

├── app/streamlit_app.py          # Streamlit UI

├── eval/                         # eval datasets + harnesses

├── tests/                        # 28 tests across all components

├── docker/                       # Dockerfiles + compose

└── .github/workflows/ci.yml      # CI: tests + eval regression gate


