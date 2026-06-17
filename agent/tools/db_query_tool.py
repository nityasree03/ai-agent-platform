"""
SQL query tool — runs read-only SQL against a sample SQLite orders/customers DB.

On first import, seeds a small sample dataset if the DB file doesn't exist yet,
so the agent has something real to query out of the box.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "sample.db"


def _ensure_seeded():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    if is_new:
        conn.executescript(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                region TEXT
            );
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                product TEXT,
                amount REAL,
                quarter TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            INSERT INTO customers VALUES
                (1, 'Acme Corp', 'West'),
                (2, 'Globex Inc', 'East'),
                (3, 'Initech', 'West'),
                (4, 'Umbrella LLC', 'South');

            INSERT INTO orders VALUES
                (1, 1, 'Widget X', 12000, 'Q1'),
                (2, 2, 'Widget X', 8500, 'Q1'),
                (3, 1, 'Widget Y', 21000, 'Q2'),
                (4, 3, 'Widget X', 15500, 'Q2'),
                (5, 4, 'Widget Y', 9800, 'Q2'),
                (6, 2, 'Widget Y', 17200, 'Q3'),
                (7, 1, 'Widget X', 13400, 'Q3');
            """
        )
        conn.commit()
    conn.close()


_ensure_seeded()

_FORBIDDEN_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "create", "attach", "pragma"}


def db_query_tool(query: str) -> dict:
    """
    Run a read-only SQL query against the sample orders/customers database.

    Args:
        query: A SELECT statement. Tables: customers(id, name, region),
               orders(id, customer_id, product, amount, quarter).

    Returns:
        {"rows": [...], "columns": [...]} on success, {"error": str} on failure.
    """
    lowered = query.strip().lower()
    if not lowered.startswith("select"):
        return {"error": "Only SELECT statements are permitted."}
    if any(kw in lowered for kw in _FORBIDDEN_KEYWORDS):
        return {"error": "Query contains a forbidden keyword (writes are not permitted)."}

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        return {"error": f"SQL error: {e}"}


TOOL_SPEC = {
    "name": "db_query",
    "description": (
        "Run a read-only SQL SELECT query over the sample sales database. "
        "Tables: customers(id, name, region), orders(id, customer_id, product, amount, quarter)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "A SELECT statement."}
        },
        "required": ["query"],
    },
}
