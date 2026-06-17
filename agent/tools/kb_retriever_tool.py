"""
Internal knowledge-base retriever tool.

Standalone here: simple keyword-overlap retrieval over a small seeded set of
internal policy/runbook documents — no external vector DB dependency
required. Swap in a real RAG retriever (Chroma/Pinecone + embeddings) later
by replacing the body of `kb_retriever_tool` and keeping the same signature.
"""
from __future__ import annotations

import re

_DOCS = [
    {
        "id": "policy-001",
        "title": "Expense Reimbursement Policy",
        "text": (
            "Employees may submit expense reimbursements within 30 days of purchase. "
            "Receipts are required for any expense over $25. Travel expenses require "
            "manager pre-approval. Reimbursements are processed within 5 business days."
        ),
    },
    {
        "id": "runbook-014",
        "title": "Production Incident Response Runbook",
        "text": (
            "On detecting a production incident: 1) Page the on-call engineer. "
            "2) Open an incident channel. 3) Assess severity (SEV1-SEV4). "
            "4) For SEV1/SEV2, notify the incident commander within 10 minutes. "
            "5) Document the timeline as you go. Rollback is preferred over forward-fix "
            "for SEV1 incidents."
        ),
    },
    {
        "id": "policy-022",
        "title": "Data Retention Policy",
        "text": (
            "Customer data is retained for 24 months after account closure unless a "
            "legal hold applies. Logs are retained for 90 days. Backups are retained "
            "for 7 years for financial records per compliance requirements."
        ),
    },
    {
        "id": "ticket-system-faq",
        "title": "Internal Ticket System FAQ",
        "text": (
            "Tickets are auto-assigned based on the component tag. SLA for P1 tickets "
            "is 4 hours response time; P2 is 1 business day; P3 is 3 business days. "
            "Escalation requires manager approval via the #escalations channel."
        ),
    },
]


def _score(query: str, text: str) -> int:
    q_words = set(re.findall(r"\w+", query.lower()))
    t_words = set(re.findall(r"\w+", text.lower()))
    return len(q_words & t_words)


def kb_retriever_tool(query: str, top_k: int = 2) -> dict:
    """
    Retrieve the most relevant internal documents for a query.

    Args:
        query: Natural-language question.
        top_k: Number of documents to return.

    Returns:
        {"results": [{"id", "title", "text", "score"}, ...]}
    """
    scored = [
        {**doc, "score": _score(query, doc["title"] + " " + doc["text"])}
        for doc in _DOCS
    ]
    scored.sort(key=lambda d: d["score"], reverse=True)
    top = [d for d in scored[:top_k] if d["score"] > 0]
    if not top:
        return {"results": [], "note": "No matching internal documents found."}
    return {"results": top}


TOOL_SPEC = {
    "name": "kb_retriever",
    "description": "Search internal policy documents and runbooks for relevant passages.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural-language question to search for."}
        },
        "required": ["query"],
    },
}
