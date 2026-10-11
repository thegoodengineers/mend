"""Write every gate decision back into neatlogs as its own trace: an audit log of Mend changing itself.

    python -m mend.audit              # backfill every round not logged yet -> evidence/gate-audit.json

Each round becomes one trace in the "mend-gate" workflow, sent with the neatlogs SDK: a WORKFLOW span
for the round, one TOOL span per keep rule ("met" / "NOT met"), and a verdict span. A neatlogs
detection on the verdict span flags every revert. (The MCP `log_trace` tool was tried first; its
traces stayed "processing" and then returned HTTP 409, see evidence/neatlogs-ingestion-11oct.md.)
"""

import json

from mend.stats import round_stats
from mend.tasks import ROOT

RUNS = ROOT / "runs"
LOG = ROOT / "evidence" / "gate-audit.json"
REPO = "https://github.com/thegoodengineers/mend"
TOKEN_SAVING = 0.15  # same value as mend.supervisor; imported there would pull in the SDK


def rounds() -> list[tuple[int, dict]]:
    out = []
    for p in sorted(RUNS.glob("*.round.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if not r.get("rejected") and "after" in r:
            out.append((len(out) + 1, r))
    return out


def checks(r: dict) -> list[tuple[str, bool, str]]:
    """(rule, met?, detail) for each keep rule that applied to this round."""
    s = round_stats(r)
    more = r["after_passed"] > r["before_passed"]
    ratio = r["after_tokens"] / r["before_tokens"]
    out = [("more tasks pass", more, f"{r['before_passed']} -> {r['after_passed']} of {r['total']}"),
           ("same tasks pass with >=15% fewer tokens", r["after_passed"] == r["before_passed"] and ratio <= 1 - TOKEN_SAVING,
            f"{r['before_tokens']:,} -> {r['after_tokens']:,} tokens (x{ratio:.3f})")]
    if "stats" in r:  # gate amendment 1 (docs/GATE.md) applied from round 8
        out += [("amendment 1: no passing task broke", s["broke"] == 0, f"{s['fixed']} fixed, {s['broke']} broke"),
                ("amendment 1: paired 95% interval below 1.0", more or s["ci_high"] < 1.0,
                 f"tokens x{s['token_ratio']} [{s['ci_low']}, {s['ci_high']}]")]
    return out


def log_round(n: int, r: dict) -> dict:
    """Log one round as a neatlogs trace (idempotent per round number). Needs neatlogs.init first."""
    import neatlogs

    done = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    if str(n) in done:
        return done[str(n)]

    @neatlogs.span(kind="TOOL", tool_name="gate_rule")
    def gate_rule(rule: str, detail: str, met: bool) -> str:
        return f"{rule}: {'met' if met else 'NOT met'} ({detail})"

    @neatlogs.span(kind="TOOL", tool_name="gate_verdict")
    def gate_verdict(title: str, commit: str, kept: bool) -> str:
        return f"GATE {'KEPT' if kept else 'REVERTED'} {commit}"

    @neatlogs.span(kind="WORKFLOW")
    def gate_round(round_no: int, title: str, before_run: str, after_run: str, diagnosis: str) -> dict:
        carrier: dict[str, str] = {}
        neatlogs.inject_trace_context(carrier)
        for rule, met, detail in checks(r):
            gate_rule(rule, detail, met)
        return {"trace_id": carrier.get("traceparent", "--").split("-")[1],
                "verdict": gate_verdict(title, r["commit"], r["kept"])}

    answer = gate_round(n, r.get("title") or "", r["before"], r["after"],
                        f"{REPO}/blob/main/{r['diagnosis'].replace(chr(92), '/')}")
    done[str(n)] = {"after": r["after"], "kept": r["kept"], **answer}
    LOG.write_text(json.dumps(done, indent=2), encoding="utf-8")
    return done[str(n)]


if __name__ == "__main__":
    import os

    import neatlogs

    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name="mend-gate")
    try:
        for n, r in rounds():
            print(n, log_round(n, r))
    finally:
        neatlogs.flush()
        neatlogs.shutdown()
