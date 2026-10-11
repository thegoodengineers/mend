"""Run the worker on the task suite and record the result.

    python -m mend.suite              # all 20 tasks
    python -m mend.suite 01 05 15     # selected tasks
    python -m mend.suite --heldout    # the held-out tasks the supervisor never sees
    python -m mend.suite --realworld  # bugs in the vendored open-source inflection library (also never seen)
    python -m mend.suite --hardware   # bugs in digital-logic designs, checked by simulation (also never seen)
    python -m mend.suite --schematics # bugs in circuit netlists, checked by circuit simulation (also never seen)
    python -m mend.suite --board      # bring-up bugs on a whole sensor board netlist (also never seen)
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import neatlogs

import tempfile
from pathlib import Path

from mend.tasks import (BOARD_FILE, HARDWARE_FILE, HELDOUT_FILE, REALWORLD_FILE, ROOT, SCHEMATICS_FILE, TASKS_FILE, load_tasks,
                        prepare)

RUNS = Path(os.environ.get("MEND_RUNS_DIR", ROOT / "runs"))  # override for side experiments


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def use_library_name(worker, library: str) -> None:
    """Point the worker's prompt at another library by name (same edit for every worker version)."""
    text = worker.PROMPT_FILE.read_text(encoding="utf-8").replace("invoicer", library)
    tmp = Path(tempfile.mkdtemp(prefix="mend-prompt-")) / "worker.md"
    tmp.write_text(text, encoding="utf-8")
    worker.PROMPT_FILE = tmp


def count_tool_calls(worker, counter: dict) -> None:
    """Wrap the worker's tool handlers (from outside, any worker version) to count calls per tool."""
    def wrap(name, fn):
        def run(work, **args):
            counter[name] = counter.get(name, 0) + 1
            return fn(work, **args)
        return run
    worker.HANDLERS = {name: wrap(name, fn) for name, fn in worker.HANDLERS.items()}


def run_suite(task_ids: list[str] | None = None, label: str = "", heldout: bool = False, realworld: bool = False,
              hardware: bool = False, schematics: bool = False, board: bool = False) -> dict:
    from mend import worker  # imported after neatlogs.init (see worker docstring)

    source = BOARD_FILE if board else SCHEMATICS_FILE if schematics else HARDWARE_FILE if hardware else REALWORLD_FILE if realworld else HELDOUT_FILE if heldout else TASKS_FILE
    tasks = [t for t in load_tasks(source) if not task_ids or t["id"] in task_ids]
    if tasks and tasks[0].get("library"):
        use_library_name(worker, tasks[0]["library"])
    label = "-".join(x for x in (label, os.environ.get("MEND_RUN_LABEL", "")) if x)  # parallel runs need distinct ids
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S") + (f"-{label}" if label else "")
    run = {
        "run_id": run_id,
        "worker_commit": git("rev-parse", "--short", "HEAD"),
        "worker_dirty": bool(git("status", "--porcelain", "mend/worker.py", "mend/prompts")),
        "model": worker.MODEL,
        "heldout": heldout or realworld or hardware or schematics or board,
        "realworld": realworld,
        "hardware": hardware,
        "domain": "board" if board else "schematics" if schematics else "hardware" if hardware else None,
        "tasks": [],
    }
    counts: dict = {}
    count_tool_calls(worker, counts)
    for task in tasks:
        work = prepare(task)
        counts.clear()
        try:
            result = worker.solve(task, work)
            result["tool_calls"] = dict(counts)
        except Exception as exc:  # an API failure on one task must not lose the whole run
            result = {"task_id": task["id"], "passed": False, "stop": "exception", "error": repr(exc)[:500]}
        finally:
            shutil.rmtree(work, ignore_errors=True)
        result["difficulty"] = task["difficulty"]
        run["tasks"].append(result)
        print(f"{task['id']} {'PASS' if result['passed'] else 'FAIL'}  turns={result.get('turns')}  stop={result.get('stop')}", flush=True)
    run["passed"] = sum(t["passed"] for t in run["tasks"])
    run["total"] = len(run["tasks"])
    run["input_tokens"] = sum(t.get("input_tokens", 0) for t in run["tasks"])
    run["output_tokens"] = sum(t.get("output_tokens", 0) for t in run["tasks"])
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{run_id}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    print(f"run {run_id}: {run['passed']}/{run['total']} passed -> runs/{run_id}.json")
    return run


if __name__ == "__main__":
    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name=os.environ.get("MEND_WORKFLOW", "mend-worker"))
    try:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        held, real, hw, sc, bd = (f"--{x}" in sys.argv for x in ("heldout", "realworld", "hardware", "schematics", "board"))
        label = "board" if bd else "schematics" if sc else "hardware" if hw else "realworld" if real else "heldout" if held else ""
        run_suite(args or None, label=label, heldout=held, realworld=real, hardware=hw, schematics=sc, board=bd)
    finally:
        neatlogs.flush()
        neatlogs.shutdown()
