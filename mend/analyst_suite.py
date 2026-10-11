"""Run the analyst agent (agents/analyst) on its questions and record the result -> runs/analyst/<run_id>.json

    python -m mend.analyst_suite            # all questions
    python -m mend.analyst_suite A01 A05    # selected questions
    python -m mend.analyst_suite --heldout  # 10 questions on clinic.db, a database the supervisor never saw

Each answer is judged by the runner, not the agent: the reference SQL in tasks/analyst.json runs on the same
database, and a number must match within 0.01 (0.1 for percentages); a name must match ignoring case.
Run files have the same shape as the worker's, so the supervisor can read them.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import neatlogs

from mend.suite import git
from mend.tasks import ROOT

TASKS = ROOT / "tasks" / "analyst.json"
RUNS = Path(os.environ.get("MEND_ANALYST_RUNS", ROOT / "runs" / "analyst"))
DB = ROOT / "agents" / "analyst" / "shop.db"
HELDOUT = (ROOT / "tasks" / "analyst_heldout.json", ROOT / "agents" / "analyst" / "clinic.db")


def expected(task: dict, db: Path = DB):
    with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as con:
        return con.execute(task["sql"]).fetchone()[0]


def correct(task: dict, answer: str | None, db: Path = DB) -> bool:
    if answer is None:
        return False
    want = expected(task, db)
    if task["kind"] == "text":
        return str(answer).strip().strip("'\"").lower() == str(want).lower()
    m = re.search(r"-?\d[\d,]*\.?\d*", str(answer))
    if not m:
        return False
    got = float(m.group(0).replace(",", ""))
    return abs(got - float(want)) <= (0.1 if "percent" in task["question"].lower() else 0.01)


def run_suite(ids: list[str] | None = None, label: str = "", heldout: bool = False) -> dict:
    from agents.analyst import agent  # after neatlogs.init
    tasks_file, db = HELDOUT if heldout else (TASKS, DB)
    agent.DB = db  # point the agent at the database without editing it (before its first call reads the schema)
    tasks = [t for t in json.loads(tasks_file.read_text(encoding="utf-8")) if not ids or t["id"] in ids]
    label = "-".join(x for x in ("heldout" if heldout else "", label) if x)
    label = "-".join(x for x in (label, os.environ.get("MEND_RUN_LABEL", "")) if x)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S") + (f"-{label}" if label else "")
    run = {"run_id": run_id, "agent": "analyst", "worker_commit": git("rev-parse", "--short", "HEAD"),
           "worker_dirty": bool(git("status", "--porcelain", "agents/analyst")), "model": agent.MODEL, "heldout": heldout,
           "db": db.name, "tasks": []}
    for task in tasks:
        try:
            result = agent.answer_question(task["id"], task["question"])
        except Exception as exc:
            result = {"task_id": task["id"], "answer": None, "stop": "exception", "error": repr(exc)[:300]}
        result["passed"] = correct(task, result.get("answer"), db)
        result["expected"] = str(expected(task, db))
        run["tasks"].append(result)
        print(f"{task['id']} {'PASS' if result['passed'] else 'FAIL'}  answer={result.get('answer')!r} expected={result['expected']}  "
              f"turns={result.get('turns')}", flush=True)
    run["passed"] = sum(t["passed"] for t in run["tasks"])
    run["total"] = len(run["tasks"])
    run["input_tokens"] = sum(t.get("input_tokens", 0) for t in run["tasks"])
    run["output_tokens"] = sum(t.get("output_tokens", 0) for t in run["tasks"])
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{run_id}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    print(f"run {run_id}: {run['passed']}/{run['total']} -> {RUNS.name}/{run_id}.json")
    return run


if __name__ == "__main__":
    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name="mend-analyst")
    try:
        run_suite([a for a in sys.argv[1:] if not a.startswith("--")] or None, heldout="--heldout" in sys.argv)
    finally:
        neatlogs.flush()
        neatlogs.shutdown()
