# AI Agent Platform — Multi-Tool Agentic Workflow

A multi-agent system that plans, routes, calls tools, and self-corrects — built around a Supervisor + Research/Data sub-agent architecture, with a planner -> executor -> reflector loop inside each sub-agent.

## Status: complete

- Core agent loop, 4 tools, mock LLM client, tests, eval harness (100% success)
- Supervisor + Research/Data sub-agents with real tool-scoping enforcement, multi-agent eval (100% success, 100% routing accuracy)
- LangSmith tracing (graceful no-op without a key), hardened eval
- FastAPI endpoints, Streamlit UI with reasoning-trace viewer, Docker, GitHub Actions CI gate
## Architecture

User query goes to a Supervisor, which classifies the task and routes it to a sub-agent: Research Agent (web_search, kb_retriever) or Data Agent (calculator, db_query). Inside each sub-agent, a Planner decides the next action, an Executor runs it if a tool was requested, and a Reflector judges the result, looping back to the Planner if the task is not yet complete.

Each sub-agent can only call its own tools, this is enforced in code (agent/nodes.py), not just by convention, and is covered by dedicated tests.
## Quickstart

Install dependencies with pip install -r requirements.txt --break-system-packages. Then run a single query through the full multi-agent pipeline with python -m agent.multi_agent_runner followed by your question in quotes. Run the test suite with pytest tests/ -v. Run the 30-scenario evaluation with python eval/run_multi_agent_eval.py. Start the API with uvicorn api.main:app --reload and visit http://127.0.0.1:8000/docs for interactive documentation. Start the Streamlit UI in a separate terminal with streamlit run app/streamlit_app.py.

## Docker

Build the image with docker build -f docker/Dockerfile -t ai-agent-platform-api . then run it with docker run -d -p 8000:8000 -e AGENT_FORCE_MOCK=1 --name agent-api ai-agent-platform-api and verify with curl http://127.0.0.1:8000/health. Both services can also be run together with docker-compose from the docker/ directory.
## LLM backend

Set nothing and the whole system runs on a deterministic, zero-cost mock LLM client. Set ANTHROPIC_API_KEY and it switches to real Claude Haiku calls automatically, with no code changes needed.

## Known limitation

The mock LLM client in agent/llm_client.py is rule-based, not a real language model. It recognizes symbolic math like 20 + 30 and explicit keywords like calculate, policy, and database, but it does not parse spelled-out arithmetic like twenty plus thirty or open-ended natural language the way a real LLM would. This only affects mock mode; real Claude Haiku calls with ANTHROPIC_API_KEY set handle natural language correctly.

## Evaluation results

The 30-scenario evaluation of the multi-agent pipeline shows 100% task success rate, 100% routing accuracy, 100% tool-call accuracy, and an average of 2.0 steps to completion.

## Tools

The calculator tool belongs to the Data Agent and performs safe AST-based arithmetic with no eval(). The db_query tool belongs to the Data Agent and runs read-only SQL over a sample orders and customers SQLite database. The kb_retriever tool belongs to the Research Agent and does keyword-overlap search over internal policy and runbook documents. The web_search tool belongs to the Research Agent and uses the Tavily API if TAVILY_API_KEY is set, otherwise it returns mock results.

## Project structure

The agent folder contains multi_agent_runner.py for Supervisor and sub-agent orchestration, supervisor.py for routing logic, nodes.py for the shared planner executor and reflector functions, llm_client.py for the Mock and Anthropic backends, tracing.py for LangSmith integration, simple_runner.py for the Week 1 single-agent loop, graph.py for the real LangGraph wiring, and a tools subfolder. The api folder contains main.py, the FastAPI app. The app folder contains streamlit_app.py, the Streamlit UI. The eval folder contains the evaluation datasets and harnesses. The tests folder contains 28 tests across all components. The docker folder contains the Dockerfiles and compose file. The .github/workflows folder contains ci.yml, which runs tests and the eval regression gate.
