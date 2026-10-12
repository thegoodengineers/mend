"""The supervisor: reads the worker's failing neatlogs traces, fixes the worker, proves it.

    python -m mend.supervisor              # one round on the latest run file
    python -m mend.supervisor <run_id>     # one round on a given run
    python -m mend.supervisor --rounds 3   # up to 3 rounds, stopping at the first revert

Round: traces of failed and most wasteful runs (MCP) -> diagnosis (Claude, structured JSON) ->
one general patch to the worker (headless Claude Code, so Entire can link the session to the
commit) -> guard + commit -> re-run the suite -> keep if more tasks pass, or the same number
pass with at least 15% fewer tokens; otherwise git revert.

If the diagnosis says its fix is a CHOICE (it trades one valid behaviour for another that no test
or token count decides), the round stops before patching and writes runs/<id>.question.json:
    python -m mend.supervisor --answer <run_id> "<decision>"   # recorded in docs/precedents.json
Every later diagnosis sees those decisions and follows them, so each question is asked once.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import neatlogs

from mend.suite import RUNS, git, run_suite
from mend.tasks import ROOT, load_tasks
from mend import detections
from mend.stats import round_stats
from mend.traces import get_trace, span_lines

MODEL = os.environ.get("MEND_MODEL", "claude-opus-5-5")
ALLOWED_FILES = {"mend/worker.py", "mend/prompts/worker.md"}
# Words that would mean the patch hard-codes knowledge of specific planted bugs.
TASK_SPECIFIC = ("money.py", "dates.py", "tax.py", "discounts.py", "invoice.py", "csv_import.py", "ledger.py",
                 "weekday", "coupon", "gst", "ROUND_HALF", "aging", "interest")
SPAN_TEXT_LIMIT = 700
WASTEFUL_SAMPLE = 3  # passing tasks with the most turns, also shown to the diagnosis
TOKEN_SAVING = 0.15  # same pass count with this much fewer tokens also counts as better
# Entire search score above which a proposed fix counts as a repeat of a past one. Calibrated on 11 Oct:
# re-proposing round 6's fix scored 94.6; four fixes never tried scored at most 42.7.
ENTIRE_REPEAT_SCORE = 80
PRECEDENTS = ROOT / "docs" / "precedents.json"  # answers people gave to judgment questions; asked once, reused

DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "failures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "failing_step": {"type": "string", "description": "the span where it went wrong, e.g. 'turn 3 write_file'"},
                    "cause": {"type": "string"},
                    "general_weakness": {"type": "string", "description": "the worker behaviour behind it, phrased so it applies to any bug"},
                },
                "required": ["task_id", "failing_step", "cause", "general_weakness"],
                "additionalProperties": False,
            },
        },
        "fix": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "short commit-style title"},
                "target_file": {"type": "string", "enum": sorted(ALLOWED_FILES)},
                "instructions": {"type": "string", "description": "exact change to make, for a coding agent"},
                "why_general": {"type": "string"},
                "guard": {
                    "type": "object",
                    "description": "A neatlogs regex detection that flags this failure in future traces: a regex on the "
                                   "OUTPUT text of one span, matching the visible symptom (e.g. an error message).",
                    "properties": {
                        "display_name": {"type": "string", "description": "starts with 'Mend: '"},
                        "span_name": {"type": "string", "enum": ["list_files", "read_file", "edit_file", "write_file", "run_tests", "solve_task"]},
                        "output_pattern": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["display_name", "span_name", "output_pattern", "description"],
                    "additionalProperties": False,
                },
                "judgment": {
                    "type": "object",
                    "description": "Is this fix a CHOICE rather than a correction? A choice trades one valid worker behaviour "
                                   "for another that neither the tests nor the token count can decide (e.g. scope of edits, "
                                   "how much to verify, what to leave untouched). If a recorded human decision already "
                                   "settles it, it is not a choice: follow that decision.",
                    "properties": {
                        "is_choice": {"type": "boolean"},
                        "question": {"type": "string", "description": "if a choice: one question for a person, with the options"},
                        "precedent_used": {"type": "string", "description": "the recorded decision this fix follows, or ''"},
                    },
                    "required": ["is_choice", "question", "precedent_used"],
                    "additionalProperties": False,
                },
            },
            "required": ["title", "target_file", "instructions", "why_general", "guard", "judgment"],
            "additionalProperties": False,
        },
    },
    "required": ["failures", "fix"],
    "additionalProperties": False,
}

SYSTEM = """You improve an AI coding agent (the "worker") by reading traces of its failed runs.
The worker fixes bugs in a small Python library using four tools. You get its source, its
system prompt, and for each failed task the bug report and the trace (spans in order, with
inputs and outputs, truncated).

Some runs failed; others passed but took many turns. Find where each run went wrong or
wasted turns, group them by the worker behaviour that caused it, and propose ONE fix to the
worker that addresses the most common cause - more tasks solved, or the same tasks in fewer
turns. The fix must improve
the worker in general - its prompt, tools or loop policy. It must never mention specific
modules, functions or bugs of the library, and never special-case a task."""


def _client():
    from anthropic import Anthropic  # after neatlogs.init

    return neatlogs.wrap(Anthropic())


def trace_digest(trace: dict) -> str:
    """Span tree plus each span's truncated input/output, in order."""
    lines = span_lines(trace)
    for s in trace.get("spans") or []:
        if s.get("type") == "workflow":
            continue
        lines.append(f"--- {s.get('type')} {s.get('name')} [{s.get('status')}]")
        lines.append(f"in:  {str(s.get('input_value', ''))[:SPAN_TEXT_LIMIT]}")
        lines.append(f"out: {str(s.get('output_value', ''))[:SPAN_TEXT_LIMIT]}")
    return "\n".join(lines)


def latest_run_id() -> str:
    return max(p.stem for p in RUNS.glob("*.json") if "." not in p.stem)


def _entire_files(sha: str) -> str:
    """Files a self-fix touched, read back from its Entire checkpoint ('' if Entire has none)."""
    try:
        out = subprocess.run(["entire", "checkpoint", "explain", sha], cwd=ROOT, capture_output=True,
                             text=True, timeout=60, encoding="utf-8", errors="replace").stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if "## Files" not in out:
        return ""
    section = out.split("## Files", 1)[1].split("──", 1)[0]
    return ", ".join(line.strip().strip("-` ") for line in section.splitlines() if line.strip().startswith("- "))


def precedents() -> list[dict]:
    return json.loads(PRECEDENTS.read_text(encoding="utf-8")) if PRECEDENTS.exists() else []


def answer(run_id: str, text: str) -> dict:
    """Record a person's answer to a pending judgment question, so the next round can follow it."""
    q = json.loads((RUNS / f"{run_id}.question.json").read_text(encoding="utf-8"))
    entry = {"question": q["question"], "answer": text, "asked_in": run_id}
    PRECEDENTS.write_text(json.dumps(precedents() + [entry], indent=2), encoding="utf-8")
    return entry


def entire_search(text: str) -> list[dict]:
    """Commits Entire's search service finds for `text` (hybrid semantic + keyword); [] if unavailable."""
    try:
        out = subprocess.run(["entire", "search", text, "--compact"], cwd=ROOT, capture_output=True, text=True,
                             timeout=120, encoding="utf-8", errors="replace").stdout
        return [r for r in json.loads(out).get("results", []) if r.get("type") == "commit"]
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return []


def repeats_reverted_fix(title: str) -> str:
    """Why this fix should not run again (Entire finds it is a reverted fix), or '' if it is new."""
    reverted = {}
    for p in sorted(RUNS.glob("*.round.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("commit") and not r.get("kept"):
            reverted[r["commit"][:7]] = r.get("title") or r["commit"]
    for hit in entire_search(title)[:3]:
        if hit.get("score", 0) >= ENTIRE_REPEAT_SCORE and hit["id"][:7] in reverted:
            return f"Entire search: repeats reverted fix {hit['id'][:7]} '{reverted[hit['id'][:7]]}' (score {hit['score']:.0f})"
    return ""


def repair_history() -> str:
    """Every fix Mend has tried on itself (kept, reverted or rejected), from round records and Entire checkpoints."""
    lines = []
    for p in sorted(RUNS.glob("*.round.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        title = r.get("title") or ""
        if not title and r.get("diagnosis"):
            text = (ROOT / r["diagnosis"].replace("\\", "/")).read_text(encoding="utf-8")
            m = re.search(r"## Chosen fix: (.+)", text)
            title = m.group(1) if m else ""
        if r.get("rejected"):
            lines.append(f"- REJECTED before running: {title} (reason: {r.get('reason')})")
            continue
        files = _entire_files(r["commit"]) if r.get("commit") else ""
        verdict = ("REVERTED BY THE GATE, THEN ACCEPTED BY A PERSON (see precedents)"
                   if r.get("human_decision", {}).get("accepted") else "KEPT" if r.get("kept") else "REVERTED")
        lines.append(f"- {verdict}: {title} "
                     f"(solved {r.get('before_passed')} -> {r.get('after_passed')}/{r.get('total')}, "
                     f"tokens {r.get('before_tokens', 0):,} -> {r.get('after_tokens', 0):,}"
                     + (f"; its Entire checkpoint shows it changed {files}" if files else "") + ")")
    return "\n".join(lines)


@neatlogs.span(kind="WORKFLOW")
def diagnose_failures(run_id: str) -> dict:
    run = json.loads((RUNS / f"{run_id}.json").read_text(encoding="utf-8"))
    reports = {t["id"]: t["report"] for t in load_tasks()}
    failed = [t for t in run["tasks"] if not t["passed"]]
    wasteful = sorted((t for t in run["tasks"] if t["passed"]), key=lambda t: -t.get("turns", 0))[:WASTEFUL_SAMPLE]
    if not failed and not wasteful:
        return {"failures": [], "fix": None}
    parts = [
        "## Worker source (mend/worker.py)\n" + (ROOT / "mend/worker.py").read_text(encoding="utf-8"),
        "## Worker system prompt (mend/prompts/worker.md)\n" + (ROOT / "mend/prompts/worker.md").read_text(encoding="utf-8"),
        "## Repair history (round records + Entire checkpoints). Do not propose a fix that repeats one already "
        "kept, reverted or rejected; build on what is there.\n" + (repair_history() or "(none yet)"),
        "## Decisions made by people (precedents). Follow them; never ask again what one of these settles.\n"
        + ("\n".join(f"- Q: {p['question']}\n  A: {p['answer']}" for p in precedents()) or "(none yet)"),
    ]
    for t in failed + wasteful:
        outcome = "Failed" if not t["passed"] else "Passed but slow"
        header = f"## {outcome}: task {t['task_id']} (stop={t.get('stop')}, turns={t.get('turns')})\nBug report: {reports[t['task_id']]}"
        try:
            body = trace_digest(get_trace(t["trace_id"])) if t.get("trace_id") else f"no trace: {t.get('error')}"
        except Exception as exc:  # one unreadable trace should not block the diagnosis
            body = f"trace unavailable: {exc}"
        parts.append(f"{header}\n{body}")
    response = _client().messages.create(
        model=MODEL, max_tokens=16000, system=SYSTEM,
        messages=[{"role": "user", "content": "\n\n".join(parts)}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": DIAGNOSIS_SCHEMA}},
    )
    diagnosis = json.loads(next(b.text for b in response.content if b.type == "text"))
    diagnosis["usage"] = {"model": MODEL, "input_tokens": response.usage.input_tokens,
                          "output_tokens": response.usage.output_tokens}
    return diagnosis


def fresh_stem(run_id: str) -> str:
    """A name for this round's diagnosis that never overwrites an earlier one (a run can be diagnosed twice)."""
    stem, n = run_id, 1
    while (RUNS / f"{stem}.diagnosis.md").exists():
        n += 1
        stem = f"{run_id}-d{n}"
    return stem


def write_diagnosis(run_id: str, diagnosis: dict) -> str:
    fix = diagnosis["fix"]
    rows = "\n".join(f"| {f['task_id']} | {f['failing_step']} | {f['cause']} | {f['general_weakness']} |"
                     for f in diagnosis["failures"])
    text = (f"# Diagnosis of run {run_id}\n\n| Task | Failing step | Cause | General weakness |\n|---|---|---|---|\n{rows}\n\n"
            f"## Chosen fix: {fix['title']}\n\nFile: `{fix['target_file']}`\n\n{fix['instructions']}\n\n"
            f"Why it is general: {fix['why_general']}\n")
    j = fix.get("judgment") or {}
    if j.get("is_choice"):
        text += f"\n## Judgment needed (not applied)\n\n{j['question']}\n"
    elif j.get("precedent_used"):
        text += f"\n## Follows a recorded human decision\n\n{j['precedent_used']}\n"
    if fix.get("guard"):
        g = fix["guard"]
        text += (f"\n## Proposed neatlogs regression guard\n\n`{g['display_name']}`: regex `{g['output_pattern']}` on the "
                 f"output of `{g['span_name']}` spans. {g['description']}\n")
    path = RUNS / f"{fresh_stem(run_id)}.diagnosis.md"
    path.write_text(text, encoding="utf-8")
    return str(path.relative_to(ROOT))


def untracked() -> set[str]:
    return set(git("ls-files", "--others", "--exclude-standard").splitlines())


def mentions_task_code(added: str) -> bool:
    """Does added diff text name specific library code? File names and identifiers (money.py, ROUND_HALF
    as in ROUND_HALF_UP) match anywhere; plain words only as whole words, so "managing" does not trip
    "aging" and "interesting" does not trip "interest"."""
    added = added.lower()
    return any(word.lower() in added if not word.isalpha() else re.search(rf"\b{re.escape(word.lower())}\b", added)
               for word in TASK_SPECIFIC)


def apply_patch(fix: dict, diagnosis_file: str, untracked_before: set[str] = frozenset()) -> tuple[bool, str]:
    """Let headless Claude Code edit the worker, then check the change stays in bounds."""
    prompt = (f"Read {diagnosis_file}. Make exactly the change it describes under 'Chosen fix', "
              f"editing only {fix['target_file']}. Keep the change small. Do not edit any other file, "
              "do not run anything, and do not mention specific library modules or bugs.")
    try:  # output is not used; discarding it also avoids decoding it with the Windows code page
        subprocess.run([shutil.which("claude") or "claude", "-p", prompt, "--allowedTools", "Read", "Edit",
                        "--permission-mode", "acceptEdits"],
                       cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    except subprocess.TimeoutExpired:
        return False, "patch step timed out"
    except FileNotFoundError:
        return False, "claude CLI not found"
    changed = set(git("diff", "--name-only").splitlines()) | (untracked() - untracked_before - {diagnosis_file})
    if not changed:
        return False, "no change made"
    if not changed <= ALLOWED_FILES:
        return False, f"touched files outside the worker: {sorted(changed - ALLOWED_FILES)}"
    diff = git("diff")
    added = "\n".join(l for l in diff.splitlines() if l.startswith("+"))
    if mentions_task_code(added):
        return False, "patch mentions specific library code (task-specific hack)"
    try:
        tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_smoke.py", "tests/test_traces.py"],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    except subprocess.TimeoutExpired:
        return False, "worker unit tests timed out"
    if tests.returncode != 0:
        return False, "worker no longer imports / unit tests fail"
    return True, f"changed {sorted(changed)}"


def discard_patch(untracked_before: set[str], keep: str) -> None:
    """Undo everything a rejected patch step touched, not just the two files it was allowed to touch."""
    subprocess.run(["git", "checkout", "--", "."], cwd=ROOT)
    for rel in untracked() - untracked_before - {keep}:
        (ROOT / rel).unlink(missing_ok=True)


def gate(before: dict, after: dict, stats: dict) -> bool:
    """The keep rule (docs/GATE.md): more tasks pass, or the same pass with at least 15% fewer tokens.
    Amendment 1: no task that passed may break, and a token-only win must hold across tasks
    (paired 95% interval entirely below 1.0), not just in the total.
    Amendment 3: when both runs carry fix audits, the patch may not raise the number of passing fixes
    the audit calls "gamed" (tests modified or a model altered)."""
    tokens = lambda r: r.get("input_tokens", 0) + r.get("output_tokens", 0)  # noqa: E731
    more = after["passed"] > before["passed"]
    cheaper = after["passed"] == before["passed"] and tokens(after) <= (1 - TOKEN_SAVING) * tokens(before)
    gamed = lambda r: sum(t.get("audit", {}).get("verdict") == "gamed" for t in r.get("tasks", []))  # noqa: E731
    audited = all(any("audit" in t for t in r.get("tasks", [])) for r in (before, after))
    no_more_gaming = not audited or gamed(after) <= gamed(before)
    return (more or cheaper) and stats["broke"] == 0 and (more or stats["ci_high"] < 1.0) and no_more_gaming


def one_round(run_id: str) -> dict:
    if git("status", "--porcelain", "--untracked-files=no"):
        sys.exit("commit or stash tracked changes first; the patch check compares against a clean tree")
    before = json.loads((RUNS / f"{run_id}.json").read_text(encoding="utf-8"))
    if before.get("heldout"):
        sys.exit("refusing to learn from a held-out run")
    diagnosis = diagnose_failures(run_id)
    if not diagnosis["fix"]:
        print("nothing failed; nothing to fix")
        return {"before": run_id, "kept": False, "reason": "no failures"}
    diagnosis_file = write_diagnosis(run_id, diagnosis)
    stem = diagnosis_file.replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".diagnosis.md")
    print(f"diagnosis -> {diagnosis_file}: {diagnosis['fix']['title']}")
    judgment = diagnosis["fix"].get("judgment") or {}
    if judgment.get("is_choice"):  # automate what isn't a choice; ask a person when it is, once
        record = {"before": run_id, "kept": False, "needs_human": True, "question": judgment["question"],
                  "title": diagnosis["fix"]["title"], "diagnosis": diagnosis_file}
        (RUNS / f"{stem}.question.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"needs a person: {judgment['question']}\n"
              f"answer with: python -m mend.supervisor --answer {stem} \"<your decision>\"")
        return record
    repeat = repeats_reverted_fix(diagnosis["fix"]["title"])  # don't pay for a re-run Entire says already failed
    untracked_before = untracked() - {diagnosis_file.replace("\\", "/")}
    ok, why = (False, repeat) if repeat else apply_patch(diagnosis["fix"], diagnosis_file.replace("\\", "/"), untracked_before)
    if not ok:
        discard_patch(untracked_before, keep=diagnosis_file.replace("\\", "/"))
        print(f"patch rejected: {why}")
        record = {"before": run_id, "kept": False, "rejected": True, "reason": why,
                  "title": diagnosis["fix"]["title"], "diagnosis": diagnosis_file}
        (RUNS / f"{stem}.rejected.round.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record
    subprocess.run(["git", "add", *ALLOWED_FILES, diagnosis_file], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"fix(worker): {diagnosis['fix']['title']}",
                    "-m", f"Proposed by the Mend supervisor from neatlogs traces of run {run_id}; see {diagnosis_file}."],
                   cwd=ROOT, check=True)
    commit = git("rev-parse", "--short", "HEAD")
    try:
        after = run_suite([t["task_id"] for t in before["tasks"]], label="after")
        stats = round_stats({"before": run_id, "after": after["run_id"], "kept": None})
    except BaseException:  # never leave an unjudged patch committed
        subprocess.run(["git", "revert", "--no-edit", "HEAD"], cwd=ROOT, check=True, capture_output=True)
        raise
    tokens = lambda r: r.get("input_tokens", 0) + r.get("output_tokens", 0)  # noqa: E731
    kept = gate(before, after, stats)
    if not kept:
        subprocess.run(["git", "revert", "--no-edit", "HEAD"], cwd=ROOT, check=True, capture_output=True)
        # The revert also removed the diagnosis committed with the patch; keep it, it is the evidence of why.
        subprocess.run(["git", "checkout", commit, "--", diagnosis_file], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-q", "-m", f"chore: keep the diagnosis of reverted round {run_id}"],
                       cwd=ROOT, check=True)
    record = {"before": run_id, "before_passed": before["passed"], "after": after["run_id"],
              "after_passed": after["passed"], "total": after["total"],
              "before_tokens": tokens(before), "after_tokens": tokens(after), "commit": commit, "kept": kept,
              "diagnosis": diagnosis_file, "title": diagnosis["fix"]["title"],
              "diagnosis_usage": diagnosis.get("usage"), "stats": {**stats, "kept": kept}}
    if kept:  # leave a neatlogs detection behind so this failure is flagged if it ever comes back
        try:
            record["guard"] = detections.create(diagnosis["fix"]["guard"], detections.group_id())
        except Exception as exc:  # a guard is a bonus; never lose the round over it
            record["guard"] = {"status": f"error: {exc}"[:300]}
    (RUNS / f"{after['run_id']}.round.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    try:  # the gate's verdict also goes into neatlogs as its own trace (mend/audit.py)
        from mend import audit
        n = next(i for i, r in audit.rounds() if r["after"] == after["run_id"])
        audit.log_round(n, record)
    except Exception as exc:  # the audit trace is a bonus; never lose the round over it
        print(f"gate audit trace not logged: {exc}")
    print(f"round: {before['passed']} -> {after['passed']} of {after['total']}, tokens {tokens(before)} -> {tokens(after)}; "
          f"{'KEPT' if kept else 'REVERTED'} {commit}")
    return record


def rounds(run_id: str, limit: int) -> list[dict]:
    """Repeat rounds: each kept fix's re-run is the next round's input. Stop at the first revert."""
    records = []
    for _ in range(limit):
        record = one_round(run_id)
        records.append(record)
        if not record["kept"] or record.get("needs_human"):
            break
        run_id = record["after"]
    return records


if __name__ == "__main__":
    # python -m mend.supervisor [run_id] [--rounds N]
    args = sys.argv[1:]
    if args[:1] == ["--answer"]:
        print(json.dumps(answer(args[1], args[2]), indent=2))
        sys.exit(0)
    limit = int(args[args.index("--rounds") + 1]) if "--rounds" in args else 1
    positional = [a for i, a in enumerate(args) if a != "--rounds" and (i == 0 or args[i - 1] != "--rounds")]
    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name="mend-self-repair")
    try:
        rounds(positional[0] if positional else latest_run_id(), limit)
    finally:
        neatlogs.flush()
        neatlogs.shutdown()
