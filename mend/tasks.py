"""Planted-bug tasks for the worker: load them, prepare a broken copy of the sandbox, run its tests.

    python -m mend.tasks --check   # every bug applies once, breaks the tests; correct code passes
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = ROOT / "sandbox"
TASKS_FILE = ROOT / "tasks" / "tasks.json"
HELDOUT_FILE = ROOT / "tasks" / "heldout.json"  # never shown to the supervisor
REALWORLD_FILE = ROOT / "tasks" / "realworld.json"  # bugs in a real open-source library; never shown either
HARDWARE_FILE = ROOT / "tasks" / "hardware.json"  # bugs in digital-logic designs (Amaranth HDL); never shown either
SCHEMATICS_FILE = ROOT / "tasks" / "schematics.json"  # bugs in circuit netlists (schematics); never shown either


def load_tasks(path: Path = TASKS_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(task: dict) -> Path:
    """A fresh temp copy of the sandbox with the task's bug applied."""
    work = Path(tempfile.mkdtemp(prefix=f"mend-{task['id']}-"))
    source = ROOT / task["sandbox"] if task.get("sandbox") else SANDBOX
    shutil.copytree(source, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for edit in task["edits"]:
        path = work / edit["file"]
        text = path.read_text(encoding="utf-8")
        if text.count(edit["find"]) != 1:
            raise ValueError(f"task {task['id']}: find text must occur exactly once in {edit['file']}")
        path.write_text(text.replace(edit["find"], edit["replace"]), encoding="utf-8")
    return work


def run_tests(work: Path, pattern: str = "", timeout: int = 60) -> tuple[bool, str]:
    """Run pytest in a sandbox copy. Returns (passed, last part of the output)."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if pattern:
        cmd += ["-k", pattern]
    try:
        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"pytest timed out after {timeout}s"
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-4000:]


def check() -> bool:
    good = True
    for root in (SANDBOX, ROOT / "realworld" / "inflection", ROOT / "hardware", ROOT / "schematics"):
        ok, _ = run_tests(root)
        print(f"correct {root.name}: {'PASS' if ok else 'FAIL'}")
        good &= ok
    for task in load_tasks() + load_tasks(HELDOUT_FILE) + load_tasks(REALWORLD_FILE) + load_tasks(HARDWARE_FILE) + load_tasks(SCHEMATICS_FILE):
        work = prepare(task)
        passed, _ = run_tests(work)
        shutil.rmtree(work, ignore_errors=True)
        print(f"task {task['id']} ({task['difficulty']}): bug {'NOT CAUGHT' if passed else 'breaks tests'}")
        good &= not passed
    return good


if __name__ == "__main__":
    sys.exit(0 if "--check" in sys.argv and check() else 1)
