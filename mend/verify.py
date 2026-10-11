"""Recompute the README's numbers from the run files and fail if any of them does not match.

    python -m mend.verify

Checks (1) every run file is internally consistent (passed count and token totals equal the sum of
its tasks) and (2) the README's result tables contain exactly the numbers the run files give.
"""

import json
import sys
from pathlib import Path

from mend.tasks import ROOT

RUNS = ROOT / "runs"
README = (ROOT / "README.md").read_text(encoding="utf-8")


def runs(folder: Path = RUNS) -> dict[str, dict]:
    return {json.loads(p.read_text(encoding="utf-8"))["run_id"]: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(folder.glob("*.json")) if p.name.count(".") == 1}


def tokens(r: dict) -> int:
    return r["input_tokens"] + r["output_tokens"]


def pct(a: float, b: float) -> str:
    return f"{(b - a) / a * 100:+.1f}%".replace("-", "−")


def expected_strings(rs: dict[str, dict]) -> list[str]:
    out = []
    for p in [*sorted(RUNS.glob("*.round.json")), *sorted((RUNS / "analyst").glob("*.round.json"))]:  # worker, then analyst
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("rejected"):
            continue
        out.append(f"{r['before_passed']} → {r['after_passed']} / {r['total']}")
        out.append(f"{r['before_tokens']:,} → {r['after_tokens']:,} ({pct(r['before_tokens'], r['after_tokens'])})")

    def group(pred):
        return [r for r in rs.values() if pred(r)]

    v0 = group(lambda r: r["total"] == 28 and r["worker_commit"] == "13defdb" and "haiku" in r["model"])
    r1 = [rs[i] for i in ("2026-10-10T09-31-07-after", "2026-10-10T09-40-55", "2026-10-10T09-51-17") if i in rs]
    if v0 and r1:
        mb, ma = (sum(map(tokens, g)) / len(g) for g in (v0, r1))
        out += [", ".join(str(r["passed"]) for r in v0), f"{mb:,.0f}", ", ".join(str(r["passed"]) for r in r1),
                f"{ma:,.0f} ({pct(mb, ma)})"]
    for kind in ("heldout", "realworld", "hardware", "schematics", "board", "security"):
        def pick(r, kind=kind):
            if kind in ("schematics", "board", "security"):
                return r.get("domain") == kind
            if kind == "hardware":
                return bool(r.get("hardware"))
            return (bool(r.get("realworld")) == (kind == "realworld") and r.get("heldout") and not r.get("hardware")
                    and not r.get("domain"))
        hb = group(lambda r: pick(r) and r["worker_commit"] == "13defdb")
        ha = group(lambda r: pick(r) and r["worker_commit"] != "13defdb")
        if hb and ha:
            mb, ma = (sum(map(tokens, g)) / len(g) for g in (hb, ha))
            out += [f"{', '.join(str(r['passed']) for r in hb)} of {hb[0]['total']}", f"{mb:,.0f}",
                    f"{', '.join(str(r['passed']) for r in ha)} of {ha[0]['total']}", f"{ma:,.0f} ({pct(mb, ma)})"]
    an = runs(RUNS / "analyst")
    for commit in dict.fromkeys(r["worker_commit"] for r in an.values()):  # the second agent, one row per version
        g = sorted((r for r in an.values() if r["worker_commit"] == commit), key=lambda r: r["run_id"].endswith("-r2"))
        out += [f"{', '.join(str(r['passed']) for r in g)} of {g[0]['total']}", " · ".join(f"{tokens(r):,}" for r in g),
                " · ".join(str(sum(t.get("turns") or 0 for t in r["tasks"])) for r in g)]
    groups = [[r for r in an.values() if r["worker_commit"] == c] for c in dict.fromkeys(r["worker_commit"] for r in an.values())]
    if len(groups) > 1:
        mb, ma = (sum(map(tokens, g)) / len(g) for g in (groups[0], groups[-1]))
        out.append(f"{mb:,.0f} → {ma:,.0f} ({pct(mb, ma)})")
    from mend.stats import all_rounds
    for i, r in enumerate(all_rounds(), 1):
        out.append(f"| {i} | {r['fixed']} / {r['broke']} | {r['p_passes']} | {r['token_ratio']} | [{r['ci_low']}, {r['ci_high']}] |")
    abl = ROOT / "evidence" / "ablation.json"
    if abl.exists():
        a = json.loads(abl.read_text(encoding="utf-8"))
        mean = sum(b["tokens"] for b in a["baseline"]) / len(a["baseline"])
        lo, hi = min(b["tokens"] for b in a["baseline"]), max(b["tokens"] for b in a["baseline"])
        out.append(f"{lo:,}–{hi:,} tokens")
        for r in a["ablated"]:
            run = json.loads((RUNS / "ablation" / f"{r['run_id']}.json").read_text(encoding="utf-8"))
            assert run["input_tokens"] + run["output_tokens"] == r["tokens"], r["run_id"]
            out.append(f"| {r['passed']}/{r['total']} | {r['tokens']:,} | {r['tokens'] / mean - 1:+.0%} |")
    fa, ip = ROOT / "evidence" / "fix-audit.json", ROOT / "evidence" / "impossible-probes.json"
    for r in (json.loads(fa.read_text(encoding="utf-8")) if fa.exists() else []):
        v = r["verdicts"]
        out.append(f"| {r['passed']}/{r['total']} | {v['restored']} | {v['equivalent']} | {v['review']} | {v['gamed']} |")
    by = {}
    for r in (json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []):
        by.setdefault(r["worker"], []).append(r)
    for w, rs in by.items():
        out.append(f"| {w} | {', '.join(str(r['cheated']) for r in rs)} | {sum(r['cheated'] for r in rs)} of {sum(r['total'] for r in rs)} | "
                   f"{', '.join(str(r['flagged']) for r in rs)} |")
    r11 = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "runs" / "r11").glob("*.json")}
    if r11:
        h = next(v for k, v in r11.items() if "heldout" in k)
        rw = next(v for k, v in r11.items() if "realworld" in k)
        out.append(f"held-out **{h['passed']}/{h['total']}**, real library\n  **{rw['passed']}/{rw['total']}**")
    usage = ROOT / "evidence" / "tool-usage.json"
    for u in (json.loads(usage.read_text(encoding="utf-8")).values() if usage.exists() else []):
        c = u["counts"]
        out.append(f"| {c.get('write_file', 0)} | {c.get('edit_file', 0) or '—'} | {c['run_tests']} | {c['llm_calls']} |")
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rs = runs()
    problems = []
    for rid, r in {**rs, **runs(RUNS / "analyst")}.items():
        if r["passed"] != sum(t["passed"] for t in r["tasks"]) or r["total"] != len(r["tasks"]):
            problems.append(f"{rid}: passed/total do not match its tasks")
        if r.get("input_tokens", 0) != sum(t.get("input_tokens", 0) for t in r["tasks"]):
            problems.append(f"{rid}: input_tokens do not match its tasks")
    pin = ROOT / "evidence" / "scorer-pin.json"  # the tests and tasks that judge the worker may not drift quietly
    if pin.exists():
        import hashlib
        recorded = json.loads(pin.read_text(encoding="utf-8"))
        for f, h in recorded.items():
            path = ROOT / f
            now = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() if path.exists() else "missing"
            if now != h:
                problems.append(f"scorer pin: {f} changed since it was pinned (scripts/pin_scorer.py)")
        print(f"scorer pin: {len(recorded)} task and test files checked")
    checks = expected_strings(rs)
    for s in checks:
        if s not in README:
            problems.append(f"README is missing the number computed from run files: {s!r}")
    print(f"{len(rs)} run files, {len(checks)} README numbers recomputed")
    for s in checks:
        print(f"  {'ok ' if s in README else 'BAD'} {s}")
    for p in problems:
        print("FAIL", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
