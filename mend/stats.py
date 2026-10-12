"""How sure is each gate decision? Paired statistics over the same tasks, before vs after a fix.

    python -m mend.stats     # -> evidence/gate-stats.json, one entry per round

The gate looks at one re-run. Because every task runs both before and after, the comparison can be
paired per task, which removes most run-to-run noise (Miller 2024, "Adding Error Bars to Evals",
arXiv:2411.00640):
- passes: exact two-sided sign test (McNemar) on the tasks that flipped between pass and fail;
- tokens: 95% paired bootstrap interval for total-after / total-before, resampling tasks.
"""

import json
import os
import random
from math import comb
from pathlib import Path

from mend.tasks import ROOT

RUNS = Path(os.environ.get("MEND_RUNS_DIR", ROOT / "runs"))  # same override as mend.suite, which writes the runs
OUT = ROOT / "evidence" / "gate-stats.json"
BOOT = 10_000


def sign_test(fixed: int, broke: int) -> float:
    """Exact two-sided p-value that fixes and breaks are equally likely (McNemar's exact test)."""
    n = fixed + broke
    if n == 0:
        return 1.0
    k = min(fixed, broke)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def token_ratio_ci(pairs: list[tuple[int, int]], seed: int = 0) -> tuple[float, float, float]:
    """Total-after / total-before, with a 95% bootstrap interval over tasks."""
    if not pairs or not sum(b for b, _ in pairs):  # nothing to compare: no evidence either way
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    ratio = sum(a for _, a in pairs) / sum(b for b, _ in pairs)
    sims = []
    for _ in range(BOOT):
        s = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        before = sum(b for b, _ in s)
        sims.append(sum(a for _, a in s) / before if before else float("inf"))
    sims.sort()
    return ratio, sims[int(0.025 * BOOT)], sims[int(0.975 * BOOT) - 1]


def round_stats(record: dict) -> dict:
    load = lambda rid: {t["task_id"]: t for t in json.loads((RUNS / f"{rid}.json").read_text(encoding="utf-8"))["tasks"]}  # noqa: E731
    before, after = load(record["before"]), load(record["after"])
    common = sorted(before.keys() & after.keys())
    fixed = sum(not before[k]["passed"] and after[k]["passed"] for k in common)
    broke = sum(before[k]["passed"] and not after[k]["passed"] for k in common)
    tok = lambda t: t.get("input_tokens", 0) + t.get("output_tokens", 0)  # noqa: E731  (a task that raised has none)
    ratio, lo, hi = token_ratio_ci([(tok(before[k]), tok(after[k])) for k in common])
    return {"before": record["before"], "after": record["after"], "kept": record["kept"], "tasks": len(common),
            "fixed": fixed, "broke": broke, "p_passes": round(sign_test(fixed, broke), 4),
            "token_ratio": round(ratio, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3)}


def all_rounds() -> list[dict]:
    out = []
    for p in sorted(RUNS.glob("*.round.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if not r.get("rejected") and "after" in r:
            out.append(round_stats(r))
    return out


if __name__ == "__main__":
    assert sign_test(0, 0) == 1.0 and sign_test(5, 0) == 0.0625 and sign_test(1, 1) == 1.0
    rows = all_rounds()
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    for i, r in enumerate(rows, 1):
        print(f"round {i}: fixed {r['fixed']} broke {r['broke']} p={r['p_passes']}  tokens x{r['token_ratio']} "
              f"[{r['ci_low']}, {r['ci_high']}]  {'kept' if r['kept'] else 'reverted'}")
