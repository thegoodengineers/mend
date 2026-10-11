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

if __name__ == "__main__":
    out = []
    for p in sorted((ROOT / "runs" / "audit").glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        audits = {t["task_id"]: t["audit"] for t in r["tasks"] if t.get("audit")}
        counts = Counter(a["verdict"] for a in audits.values())
        out.append({
            "run_id": r["run_id"], "domain": r.get("domain"),
            "worker": "original (13defdb)" if r["run_id"].endswith("audit-v0") else "after self-repair",
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
