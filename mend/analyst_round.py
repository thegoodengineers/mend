"""Mend on a second, different agent: one self-repair round for the data analyst (agents/analyst).

    python -m mend.analyst_round <analyst_run_id>     (a run file in runs/analyst/)

The same loop as for the worker: the supervisor reads the analyst's failed and slowest traces back over the
neatlogs MCP server, writes a diagnosis, headless Claude Code patches only agents/analyst/agent.py or
agents/analyst/prompt.md, a guard rejects anything question-specific, and the analyst re-runs all questions.
Keep rule = supervisor.gate itself (docs/GATE.md rule 4 + amendment 1): more questions right, or the same with at
least 15% fewer tokens whose paired 95% interval is below 1, and no question that was right may go wrong.
"""

import copy
import json
import os
import re
import subprocess
import sys

import neatlogs

from mend import supervisor as sup
from mend.analyst_suite import RUNS, TASKS, run_suite
from mend.stats import sign_test, token_ratio_ci
from mend.suite import git
from mend.tasks import ROOT

ALLOWED = {"agents/analyst/agent.py", "agents/analyst/prompt.md"}
SCHEMA = copy.deepcopy(sup.DIAGNOSIS_SCHEMA)
SCHEMA["properties"]["fix"]["properties"]["target_file"]["enum"] = sorted(ALLOWED)
SCHEMA["properties"]["fix"]["properties"]["guard"]["properties"]["span_name"]["enum"] = ["list_tables", "describe", "run_sql", "answer_question"]
SYSTEM = """You improve an AI data-analyst agent by reading traces of its runs. The analyst answers questions about a
shop's SQLite database with four tools (list_tables, describe, run_sql, finish). You get its source, its system
prompt, and for each question that failed or took the most turns: the question and the trace (spans in order,
with inputs and outputs, truncated). Find where runs went wrong or wasted turns, group them by the behaviour
behind them, and propose ONE fix to the analyst (prompt, tools or loop policy) that addresses the most common
cause: more questions answered correctly, or the same answers in fewer turns and tokens. The fix must be general:
never mention specific questions, products, categories, countries, dates, numbers or answers."""


def task_words() -> set[str]:
    """Words a general fix may not contain: every value that appears in a question's answer or wording."""
    import sqlite3
    words = set()
    with sqlite3.connect(ROOT / "agents" / "analyst" / "shop.db") as con:
        for table, col in (("products", "name"), ("products", "category"), ("customers", "country")):
            words |= {str(r[0]).lower() for r in con.execute(f"SELECT DISTINCT {col} FROM {table}") if r[0]}
    words |= {"2025-", "2026-", "december", "january", "february"}
    return words


def question_words(text: str) -> list[str]:
    return sorted(w for w in task_words() if re.search(rf"\b{re.escape(w)}\b", text.lower()))


@neatlogs.span(kind="WORKFLOW")
def diagnose(run: dict) -> dict:
    questions = {t["id"]: t["question"] for t in json.loads(TASKS.read_text(encoding="utf-8"))}
    failed = [t for t in run["tasks"] if not t["passed"]]
    slow = sorted((t for t in run["tasks"] if t["passed"]), key=lambda t: -t.get("turns", 0))[:sup.WASTEFUL_SAMPLE]
    parts = [f"## Analyst source ({f})\n" + (ROOT / f).read_text(encoding="utf-8") for f in sorted(ALLOWED)]
    history = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUNS.glob("*.round.json"))]
    parts.append("## Earlier analyst rounds (do not repeat one)\n" + ("\n".join(
        f"- {'KEPT' if h['kept'] else 'REVERTED'}: {h['title']}" for h in history) or "(none yet)"))
    for t in failed + slow:
        head = f"## {'Wrong answer' if not t['passed'] else 'Right but slow'}: {t['task_id']} (turns={t.get('turns')})\nQuestion: {questions[t['task_id']]}"
        try:
            body = sup.trace_digest(sup.get_trace(t["trace_id"])) if t.get("trace_id") else f"no trace: {t.get('error')}"
        except Exception as exc:
            body = f"trace unavailable: {exc}"
        parts.append(f"{head}\n{body}")
    response = sup._client().messages.create(model=sup.MODEL, max_tokens=16000, system=SYSTEM,
                                             messages=[{"role": "user", "content": "\n\n".join(parts)}],
                                             output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}})
    d = json.loads(next(b.text for b in response.content if b.type == "text"))
    d["usage"] = {"model": sup.MODEL, "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    return d


def apply_patch(fix: dict, diagnosis_file: str) -> tuple[bool, str]:
    prompt = (f"Read {diagnosis_file}. Make exactly the change it describes under 'Chosen fix', editing only {fix['target_file']}. "
              "Keep the change small. Do not edit any other file, do not run anything, and do not mention specific questions or answers.")
    subprocess.run(["claude", "-p", prompt, "--allowedTools", "Read", "Edit", "--permission-mode", "acceptEdits"],
                   cwd=ROOT, capture_output=True, text=True, timeout=600)
    changed = set(git("diff", "--name-only").splitlines())
    if not changed:
        return False, "no change made"
    if not changed <= ALLOWED:
        return False, f"touched files outside the analyst: {sorted(changed - ALLOWED)}"
    hits = question_words("\n".join(l for l in git("diff").lower().splitlines() if l.startswith("+")))
    if hits:
        return False, f"patch mentions question-specific words: {hits}"
    ok = subprocess.run([sys.executable, "-c", "import agents.analyst.agent"], cwd=ROOT, capture_output=True).returncode == 0
    return (True, f"changed {sorted(changed)}") if ok else (False, "analyst no longer imports")


def keep(before: dict, after: dict) -> tuple[bool, dict]:
    b, a = {t["task_id"]: t for t in before["tasks"]}, {t["task_id"]: t for t in after["tasks"]}
    common = sorted(b.keys() & a.keys())
    fixed = sum(not b[k]["passed"] and a[k]["passed"] for k in common)
    broke = sum(b[k]["passed"] and not a[k]["passed"] for k in common)
    tok = lambda t: t.get("input_tokens", 0) + t.get("output_tokens", 0)  # noqa: E731
    ratio, lo, hi = token_ratio_ci([(tok(b[k]), tok(a[k])) for k in common])
    stats = {"fixed": fixed, "broke": broke, "p_passes": round(sign_test(fixed, broke), 4),
             "token_ratio": round(ratio, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3)}
    return sup.gate(before, after, stats), stats  # the worker's gate, unchanged


def analyst_round(run_id: str) -> dict:
    if git("status", "--porcelain", "--untracked-files=no"):
        sys.exit("commit or stash tracked changes first")
    before = json.loads((RUNS / f"{run_id}.json").read_text(encoding="utf-8"))
    d = diagnose(before)
    fix = d["fix"]
    diag_file = RUNS / f"{run_id}.diagnosis.md"
    rows = "\n".join(f"| {f['task_id']} | {f['failing_step']} | {f['cause']} | {f['general_weakness']} |" for f in d["failures"])
    diag_file.write_text(f"# Diagnosis of analyst run {run_id}\n\n| Question | Failing step | Cause | General weakness |\n|---|---|---|---|\n{rows}\n\n"
                         f"## Chosen fix: {fix['title']}\n\nFile: `{fix['target_file']}`\n\n{fix['instructions']}\n\nWhy it is general: {fix['why_general']}\n",
                         encoding="utf-8")
    rel = str(diag_file.relative_to(ROOT)).replace("\\", "/")
    print(f"diagnosis -> {rel}: {fix['title']}")
    ok, why = apply_patch(fix, rel)
    if not ok:
        subprocess.run(["git", "checkout", "--", *ALLOWED], cwd=ROOT)
        print(f"patch rejected: {why}")
        return {"kept": False, "rejected": True, "reason": why}
    subprocess.run(["git", "add", *ALLOWED, rel], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"fix(analyst): {fix['title']}",
                    "-m", f"Mend on a second agent: proposed by the supervisor from neatlogs traces of analyst run {run_id}; see {rel}."], cwd=ROOT, check=True)
    commit = git("rev-parse", "--short", "HEAD")
    after = run_suite(label="after")
    kept, stats = keep(before, after)
    if not kept:
        subprocess.run(["git", "revert", "--no-edit", "HEAD"], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "checkout", commit, "--", rel], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-q", "-m", f"chore: keep the diagnosis of reverted analyst round {run_id}"], cwd=ROOT, check=True)
    tokens = lambda r: r["input_tokens"] + r["output_tokens"]  # noqa: E731
    record = {"agent": "analyst", "before": run_id, "after": after["run_id"], "before_passed": before["passed"],
              "after_passed": after["passed"], "total": after["total"], "before_tokens": tokens(before),
              "after_tokens": tokens(after), "commit": commit, "kept": kept, "title": fix["title"], "diagnosis": rel,
              "stats": stats, "diagnosis_usage": d.get("usage")}
    (RUNS / f"{after['run_id']}.round.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"analyst round: {before['passed']} -> {after['passed']} of {after['total']}, tokens {tokens(before)} -> {tokens(after)} "
          f"(x{stats['token_ratio']} [{stats['ci_low']}, {stats['ci_high']}]); {'KEPT' if kept else 'REVERTED'} {commit}")
    return record


if __name__ == "__main__":
    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name="mend-self-repair")
    try:
        analyst_round(sys.argv[1])
    finally:
        neatlogs.flush()
        neatlogs.shutdown()
