"""
Multi-agent evaluation harness.

Same 30-scenario dataset as Week 1's eval, but run through the Supervisor +
sub-agent pipeline instead of the single-agent loop. Adds one new metric on
top of the Week 1 set:

  - Routing Accuracy — % of scenarios where the Supervisor picked the
    sub-agent that actually owns the expected tool for that scenario.

Usage:
    python3 eval/run_multi_agent_eval.py
Writes:
    eval/multi_agent_eval_results.json
    eval/multi_agent_eval_report.html
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("AGENT_FORCE_MOCK", "1")

from agent.multi_agent_runner import run_multi_agent
from agent.supervisor import SUB_AGENT_TOOLS

DATASET_PATH = Path(__file__).parent / "task_dataset.json"
RESULTS_JSON_PATH = Path(__file__).parent / "multi_agent_eval_results.json"
RESULTS_HTML_PATH = Path(__file__).parent / "multi_agent_eval_report.html"

# Reverse lookup: which sub-agent owns a given tool.
TOOL_TO_AGENT = {tool: agent for agent, tools in SUB_AGENT_TOOLS.items() for tool in tools}


def _first_tool_called(trace: list[dict]) -> str | None:
    return next((step["tool"] for step in trace if step["node"] == "executor"), None)


def run_eval() -> dict:
    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    per_task_results = []
    start = time.time()

    for scenario in dataset:
        result = run_multi_agent(scenario["query"])
        trace = result.get("trace", [])
        first_tool = _first_tool_called(trace)
        answer = result.get("final_answer", "")
        actual_route = result.get("route")
        expected_route = TOOL_TO_AGENT.get(scenario["expects_tool"])

        tool_correct = first_tool == scenario["expects_tool"]
        routing_correct = actual_route == expected_route
        answer_correct = (
            scenario["expects_in_answer"] is None
            or str(scenario["expects_in_answer"]) in answer
        )
        success = tool_correct and answer_correct
        retried = result.get("self_correction_count", 0) > 0

        per_task_results.append({
            "id": scenario["id"],
            "query": scenario["query"],
            "expected_route": expected_route,
            "actual_route": actual_route,
            "routing_correct": routing_correct,
            "expected_tool": scenario["expects_tool"],
            "actual_tool": first_tool,
            "tool_correct": tool_correct,
            "answer_correct": answer_correct,
            "success": success,
            "steps": result.get("steps", 0),
            "tool_call_count": result.get("tool_call_count", 0),
            "self_correction_count": result.get("self_correction_count", 0),
            "retried": retried,
            "final_answer": answer,
            "total_tokens": sum(s.get("tokens", 0) for s in trace),
        })

    elapsed = time.time() - start
    n = len(per_task_results)
    summary = {
        "n_scenarios": n,
        "success_rate": sum(r["success"] for r in per_task_results) / n,
        "routing_accuracy": sum(r["routing_correct"] for r in per_task_results) / n,
        "tool_call_accuracy": sum(r["tool_correct"] for r in per_task_results) / n,
        "avg_steps_to_completion": sum(r["steps"] for r in per_task_results) / n,
        "self_correction_rate": sum(r["retried"] for r in per_task_results) / n,
        "avg_tokens_per_task": sum(r["total_tokens"] for r in per_task_results) / n,
        "total_eval_time_s": round(elapsed, 2),
        "per_task": per_task_results,
    }
    return summary


def write_html_report(summary: dict):
    rows = "".join(
        f"<tr><td>{r['id']}</td><td>{r['query']}</td><td>{r['expected_route']}</td>"
        f"<td>{r['actual_route']}</td><td>{'OK' if r['routing_correct'] else 'FAIL'}</td>"
        f"<td>{r['expected_tool']}</td><td>{r['actual_tool']}</td>"
        f"<td>{'OK' if r['success'] else 'FAIL'}</td><td>{r['steps']}</td></tr>"
        for r in summary["per_task"]
    )
    html = f"""<!DOCTYPE html>
<html><head><title>Multi-Agent Eval Report</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 2rem; color: #222; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }}
th {{ background: #f5f5f5; }}
.metric {{ display: inline-block; margin: 0 1.5rem 1rem 0; }}
.metric .value {{ font-size: 1.8rem; font-weight: 700; }}
.metric .label {{ font-size: 0.85rem; color: #666; }}
</style></head>
<body>
<h1>AI Agent Platform — Multi-Agent Evaluation Report</h1>
<div>
  <div class="metric"><div class="value">{summary['success_rate']:.0%}</div><div class="label">Task Success Rate</div></div>
  <div class="metric"><div class="value">{summary['routing_accuracy']:.0%}</div><div class="label">Routing Accuracy</div></div>
  <div class="metric"><div class="value">{summary['tool_call_accuracy']:.0%}</div><div class="label">Tool-Call Accuracy</div></div>
  <div class="metric"><div class="value">{summary['avg_steps_to_completion']:.1f}</div><div class="label">Avg Steps-to-Completion</div></div>
  <div class="metric"><div class="value">{summary['self_correction_rate']:.0%}</div><div class="label">Self-Correction Rate</div></div>
</div>
<h2>Per-Scenario Results ({summary['n_scenarios']} scenarios)</h2>
<table>
<tr><th>#</th><th>Query</th><th>Expected Route</th><th>Actual Route</th><th>Routing</th><th>Expected Tool</th><th>Actual Tool</th><th>Success</th><th>Steps</th></tr>
{rows}
</table>
</body></html>"""
    RESULTS_HTML_PATH.write_text(html)


if __name__ == "__main__":
    summary = run_eval()

    with open(RESULTS_JSON_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    write_html_report(summary)

    print(f"Scenarios run:        {summary['n_scenarios']}")
    print(f"Success rate:         {summary['success_rate']:.1%}")
    print(f"Routing accuracy:     {summary['routing_accuracy']:.1%}")
    print(f"Tool-call accuracy:   {summary['tool_call_accuracy']:.1%}")
    print(f"Avg steps/task:       {summary['avg_steps_to_completion']:.2f}")
    print(f"Self-correction rate: {summary['self_correction_rate']:.1%}")
    print(f"\nReports written to:")
    print(f"  {RESULTS_JSON_PATH}")
    print(f"  {RESULTS_HTML_PATH}")
