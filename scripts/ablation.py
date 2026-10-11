"""Leave-one-out ablation: today's worker with one kept fix removed -> evidence/ablation.json

    python scripts/ablation.py

Each ablated worker is today's worker plus `git revert <fix>` (made in a scratch worktree), run once
on the 29 training tasks with MEND_RUNS_DIR=runs/ablation. It is compared against the three runs
of today's worker. Rounds 1 and 4 cannot be removed alone: their reverts conflict with later fixes
that build on them.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# revert commit made in the scratch worktree -> (round, kept fix it removes)
ABLATED = {"348dc6d": (2, "f9dae91"), "8d2a1c9": (3, "931ea51"), "b5db7fb": (5, "c07f702")}
BASELINE = ["2026-10-10T11-50-52-after", "2026-10-10T13-23-02", "2026-10-10T13-28-51"]  # today's worker


def load(path: Path) -> dict:
    r = json.loads(path.read_text(encoding="utf-8"))
    return {"run_id": r["run_id"], "passed": r["passed"], "total": r["total"],
            "tokens": r["input_tokens"] + r["output_tokens"], "worker_commit": r["worker_commit"]}


if __name__ == "__main__":
    base = [load(ROOT / "runs" / f"{b}.json") for b in BASELINE]
    rows = []
    for p in sorted((ROOT / "runs" / "ablation").glob("*.json")):
        r = load(p)
        rnd, fix = ABLATED[r["worker_commit"]]
        rows.append({**r, "round": rnd, "removed": fix})
    lo, hi = min(b["tokens"] for b in base), max(b["tokens"] for b in base)
    out = {"baseline": base, "ablated": sorted(rows, key=lambda r: r["round"]),
           "not_removable_alone": {"1": "e8a6baf", "4": "7e2148e"}}
    (ROOT / "evidence" / "ablation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"today's worker: {[b['passed'] for b in base]} of 29, tokens {lo:,}-{hi:,}")
    for r in out["ablated"]:
        print(f"without round {r['round']} ({r['removed']}): {r['passed']}/{r['total']}, tokens {r['tokens']:,} "
              f"({r['tokens'] / (sum(b['tokens'] for b in base) / 3) - 1:+.0%} vs mean)")
