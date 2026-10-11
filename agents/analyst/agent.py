"""A second, different agent for Mend to repair: a data analyst that answers questions over agents/analyst/shop.db.

Tools: list_tables, describe(table), run_sql(query) on a read-only connection, finish(answer). Manual tool loop so
neatlogs traces every model call and every tool call. Deliberately plain (like the worker's original version):
Mend's job is to read its traces and make it reliable. Callers run neatlogs.init(...) before importing this.
"""

import os
import sqlite3
from pathlib import Path

import neatlogs

MODEL = os.environ.get("MEND_ANALYST_MODEL", "claude-haiku-4-5")
MAX_TURNS = 12
HERE = Path(__file__).resolve().parent
PROMPT_FILE = HERE / "prompt.md"
DB = HERE / "shop.db"
MAX_ROWS = 50

TOOLS = [
    {"name": "list_tables", "description": "List the tables in the shop database.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "describe", "description": "Show a table's columns and three sample rows.",
     "input_schema": {"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]}},
    {"name": "run_sql", "description": "Run one read-only SQL query (SQLite) and get up to 50 rows back.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "finish", "description": "Give the final answer to the question: just the value (a number or a name).",
     "input_schema": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}},
]


def _db() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)


@neatlogs.span(kind="TOOL", tool_name="list_tables")
def list_tables() -> str:
    with _db() as con:
        return "\n".join(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"))


@neatlogs.span(kind="TOOL", tool_name="describe")
def describe(table: str) -> str:
    with _db() as con:
        cols = con.execute(f"PRAGMA table_info({table})").fetchall()
        if not cols:
            raise ValueError(f"no table named {table}")
        rows = con.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
    return "columns: " + ", ".join(f"{c[1]} {c[2]}" for c in cols) + "\nsample: " + "\n".join(map(str, rows))


@neatlogs.span(kind="TOOL", tool_name="run_sql")
def run_sql(query: str) -> str:
    with _db() as con:
        cur = con.execute(query)
        rows = cur.fetchmany(MAX_ROWS + 1)
        head = [d[0] for d in cur.description or []]
    more = f"\n... (more than {MAX_ROWS} rows)" if len(rows) > MAX_ROWS else ""
    return " | ".join(head) + "\n" + "\n".join(map(str, rows[:MAX_ROWS])) + more


HANDLERS = {"list_tables": lambda **a: list_tables(), "describe": lambda **a: describe(**a), "run_sql": lambda **a: run_sql(**a)}

_client = None


def client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = neatlogs.wrap(Anthropic())
    return _client


def current_trace_id() -> str | None:
    carrier: dict[str, str] = {}
    if neatlogs.inject_trace_context(carrier) and "traceparent" in carrier:
        return carrier["traceparent"].split("-")[1]
    return None


@neatlogs.span(kind="WORKFLOW")
def answer_question(task_id: str, question: str) -> dict:
    result = {"task_id": task_id, "trace_id": current_trace_id(), "turns": 0, "input_tokens": 0, "output_tokens": 0,
              "stop": None, "answer": None}
    messages = [{"role": "user", "content": f"Question: {question}"}]
    system = PROMPT_FILE.read_text(encoding="utf-8")
    while result["turns"] < MAX_TURNS:
        result["turns"] += 1
        response = client().messages.create(model=MODEL, max_tokens=4000, system=system, tools=TOOLS, messages=messages)
        result["input_tokens"] += response.usage.input_tokens
        result["output_tokens"] += response.usage.output_tokens
        result["stop"] = response.stop_reason
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return result
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "finish":
                result["answer"], result["stop"] = str(block.input.get("answer", "")).strip(), "finish"
                return result
            try:
                content, is_error = HANDLERS[block.name](**block.input), False
            except Exception as exc:  # report tool failures back to the model
                content, is_error = f"Error: {exc}", True
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": content.strip() or "(no rows)",
                                 "is_error": is_error})
        messages.append({"role": "user", "content": tool_results or [{"type": "text", "text": "(no tool result; call finish with the answer)"}]})
    result["stop"] = "max_turns"
    return result
