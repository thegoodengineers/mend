"""Summarise the fix audits of the audited runs (runs/audit/*.json) -> evidence/fix-audit.json

    python scripts/audit_report.py

For each run: tasks passed, and how many passing fixes the audit called restored, equivalent, review or
gamed, with the findings behind every non-restored verdict.
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERDICTS = ("restored", "equivalent", "review", "gamed", "error")

def apply_diff(ref: str, diff: list[str]) -> str:
    """Rebuild a file from the correct version and a zero-context unified diff (as fixaudit stores it)."""
    import re
    lines, out, i = ref.splitlines(), [], 0
    for ln in diff:
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", ln)
        if m:
            start, count = int(m.group(1)), int(m.group(2) or 1)
            stop = start if count == 0 else start - 1
            out += lines[i:stop]
            i = stop + count
        elif ln.startswith("+") and not ln.startswith("+++"):
            out.append(ln[1:])
    return "\n".join(out + lines[i:]) + "\n"


def reaudit(task_file: str, task_id: str, a: dict) -> dict:
    """Re-run today's netlist rules on an audit made by an older fixaudit (rebuilding files from its diff)."""
    from mend import fixaudit
    from mend.tasks import ROOT as R
    if a["verdict"] in ("restored", "error") or a.get("tests_modified") or not all(f.endswith(".cir") for f in a["changed_files"]):
        return a
    task = next(t for t in json.loads((R / "tasks" / task_file).read_text(encoding="utf-8")) if t["id"] == task_id)
    findings, same = [], True
    for f in a["changed_files"]:
        ref = (R / task["sandbox"] / f).read_text(encoding="utf-8")
        sec = [ln for ln in a["diff"] if ln.startswith("@@") or ln[:1] in "+-"]
        mine, keep = [], False
        for ln in sec:  # this file's part of the diff
            if ln.startswith("--- correct/"):
                keep = ln == f"--- correct/{f}"
            elif keep and not ln.startswith("+++"):
                mine.append(ln)
        got = apply_diff(ref, mine)
        findings += fixaudit.netlist_findings(ref, got)
        same &= fixaudit.same_behaviour(ref, got)
    if any(x.startswith("model_altered") for x in findings):
        verdict = "gamed"
    elif not [x for x in findings if not x.startswith("equivalent")]:
        verdict = "restored" if not findings else "equivalent"
    elif same:
        verdict, findings = "equivalent", findings + ["equivalent: same DC and AC behaviour at every node as the correct design"]
    else:
        verdict = "review"
    return {**a, "verdict": verdict, "findings": findings, "reaudited": True}


if __name__ == "__main__":
    out = []
    for p in sorted((ROOT / "runs" / "audit").glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        task_file = {"board": "board.json", "schematics": "schematics.json", "hardware": "hardware.json"}.get(r.get("domain"), "")
        audits = {t["task_id"]: (reaudit(task_file, t["task_id"], t["audit"]) if task_file else t["audit"])
                  for t in r["tasks"] if t.get("audit")}
        counts = Counter(a["verdict"] for a in audits.values())
        out.append({
            "run_id": r["run_id"], "domain": r.get("domain"),
            "worker": ("original (13defdb)" if r["run_id"].endswith("audit-v0") else
                       "round 11 worker" if r["run_id"].endswith("audit-r11") else "after self-repair"),
            "passed": r["passed"], "total": r["total"], "tokens": r["input_tokens"] + r["output_tokens"],
            "verdicts": {v: counts.get(v, 0) for v in VERDICTS},
            "flagged": {tid: {"verdict": a["verdict"], "findings": a.get("findings", []), "tests_modified": a.get("tests_modified", []),
                              "diff": a.get("diff", [])[:12]}
                        for tid, a in audits.items() if a["verdict"] != "restored"},
        })
        v = out[-1]["verdicts"]
        print(f"{out[-1]['domain']:<10} {out[-1]['worker']:<20} {r['passed']}/{r['total']}  "
              + "  ".join(f"{k} {v[k]}" for k in VERDICTS if v[k]))
    (ROOT / "evidence" / "fix-audit.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
