"""Read back how each worker handled each board bug, from the neatlogs traces -> evidence/board-agent-logs.json

    python scripts/board_logs.py

For every task in the repaired worker's board run: the bug report, each tool call with a short input and
output, and the worker's final summary. For the original worker: whether it passed, its turns, and the
first sentence it wrote. board.html shows this as the chat log next to the board.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mend.tasks import BOARD_FILE, load_tasks  # noqa: E402
from mend.traces import get_trace  # noqa: E402

REPAIRED, ORIGINAL = "2026-10-11T11-51-29-board-r2", "2026-10-11T11-51-29-board-v0"


def short(text, n=220) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def steps(trace: dict) -> list[dict]:
    spans = [s for s in trace.get("spans") or [] if s.get("type") == "tool_call"]
    spans.sort(key=lambda s: s.get("start_time") or s.get("timestamp") or "")
    out = []
    for s in spans:
        args, edit = s.get("input_value", ""), None
        try:
            parsed = json.loads(args) if isinstance(args, str) else args
            if isinstance(parsed, dict) and "old" in parsed:  # an edit: keep the before/after lines whole
                edit = {"path": parsed.get("path"), "old": parsed["old"].strip()[:400], "new": parsed.get("new", "").strip()[:400]}
            if isinstance(parsed, dict):
                args = ", ".join(f"{k}={v}" for k, v in parsed.items() if k not in ("work",))
        except ValueError:
            pass
        out.append({"tool": s.get("name"), "input": short(args, 160), "output": short(s.get("output_value"), 260), "edit": edit})
    return out


if __name__ == "__main__":
    reports = {t["id"]: t for t in load_tasks(BOARD_FILE)}
    rep = json.loads((ROOT / "runs" / f"{REPAIRED}.json").read_text(encoding="utf-8"))
    org = {t["task_id"]: t for t in json.loads((ROOT / "runs" / f"{ORIGINAL}.json").read_text(encoding="utf-8"))["tasks"]}
    logs = {}
    for t in rep["tasks"]:
        tid = t["task_id"]
        o = org[tid]
        logs[tid] = {
            "title": reports[tid]["title"], "report": reports[tid]["report"],
            "repaired": {"run": REPAIRED, "trace_id": t["trace_id"], "passed": t["passed"], "turns": t["turns"],
                         "tokens": t["input_tokens"] + t["output_tokens"], "steps": steps(get_trace(t["trace_id"])),
                         "summary": short(t.get("summary"), 400)},
            "original": {"run": ORIGINAL, "passed": o["passed"], "turns": o["turns"],
                         "tokens": o["input_tokens"] + o["output_tokens"],
                         "said": short(re.split(r"(?<=[.!?])\s", (o.get("summary") or "").strip())[0], 240)},
        }
        print(tid, len(logs[tid]["repaired"]["steps"]), "steps; original passed:", o["passed"])
    (ROOT / "evidence" / "board-agent-logs.json").write_text(json.dumps(logs, indent=1, ensure_ascii=False), encoding="utf-8")
