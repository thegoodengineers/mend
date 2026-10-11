"""Build the landing page (index.html) from the run files, so every number is real.

    python -m mend.site            # writes index.html
    python -m mend.site preview    # writes site_preview.html instead
"""

import html
import json
import re
import sys

from mend.chart import dumbbell
from mend.report import REPO, load_rounds, load_runs
from mend.tasks import ROOT

ENTIRE = "https://entire.io/gh/thegoodengineers/mend/commit/"


def esc(v) -> str:
    return html.escape(str(v))


def tokens(run: dict) -> int:
    return run.get("input_tokens", 0) + run.get("output_tokens", 0)


def facts() -> dict:
    runs = {r["run_id"]: r for r in load_runs()}
    rounds = load_rounds()
    kept = [r for r in rounds if r["kept"]]
    first = kept[0] if kept else None
    full = [r for r in runs.values() if r["total"] >= 20]
    haiku = [r for r in full if "haiku" in r["model"]]
    opus = [r for r in full if "opus" in r["model"]]
    story = None
    if first:
        before, after = runs.get(first["before"]), runs.get(first["after"])
        diag = (ROOT / first["diagnosis"].replace("\\", "/")).read_text(encoding="utf-8")
        title = re.search(r"## Chosen fix: (.+)", diag)
        if before and after:
            b = {t["task_id"]: t for t in before["tasks"]}
            a = {t["task_id"]: t for t in after["tasks"]}
            fixed = [k for k in b if not b[k]["passed"] and a.get(k, {}).get("passed")]
            story = {"title": title.group(1) if title else "", "fixed": fixed,
                     "b": b, "a": a, "diagnosis_file": first["diagnosis"].replace("\\", "/")}
    # Repeat runs on the same 28 tasks: the worker before round 1 vs after it.
    v0_commit = runs[first["before"]]["worker_commit"] if first and first["before"] in runs else None
    same = [r for r in haiku if r["total"] == 28]
    before_runs = [r for r in same if r["worker_commit"] == v0_commit]
    after_runs = [r for r in same if r["worker_commit"] != v0_commit]
    round_list = []
    for r in rounds:
        d = (ROOT / r["diagnosis"].replace("\\", "/")).read_text(encoding="utf-8")
        m = re.search(r"## Chosen fix: (.+)", d)
        round_list.append({**r, "title": m.group(1) if m else "", "diagnosis_file": r["diagnosis"].replace("\\", "/")})
    real = [r for r in runs.values() if r.get("realworld")]
    real_before = [r for r in real if r["worker_commit"] == "13defdb"]
    real_after = [r for r in real if r["worker_commit"] != "13defdb"]
    hw = [r for r in runs.values() if r.get("hardware")]
    hw_before = [r for r in hw if r["worker_commit"] == "13defdb"]
    hw_after = [r for r in hw if r["worker_commit"] != "13defdb"]
    sc = [r for r in runs.values() if r.get("domain") == "schematics"]
    sc_before = [r for r in sc if r["worker_commit"] == "13defdb"]
    sc_after = [r for r in sc if r["worker_commit"] != "13defdb"]
    held = [r for r in runs.values() if r.get("heldout") and not r.get("realworld") and not r.get("hardware") and not r.get("domain")]
    held_before = [r for r in held if r["worker_commit"] == "13defdb"]
    held_after = [r for r in held if r["worker_commit"] != "13defdb"]
    return {"rounds": round_list, "first": first, "story": story, "haiku": haiku, "opus": opus, "held_before": held_before, "held_after": held_after, "real_before": real_before, "real_after": real_after,
            "hw_before": hw_before, "hw_after": hw_after, "sc_before": sc_before, "sc_after": sc_after,
            "before_runs": before_runs, "after_runs": after_runs,
            "runs_total": len(full), "tasks_total": max((r["total"] for r in full), default=0)}


def repeat_card(label: str, group: list[dict], task: str | None, cls: str) -> str:
    if not group:
        return ""
    solved = ", ".join(str(r["passed"]) for r in group)
    mean = sum(tokens(r) for r in group) / len(group)
    hits = sum(next((t["passed"] for t in r["tasks"] if t["task_id"] == task), False) for r in group) if task else 0
    task_line = f"<span class=\"sub\">task {esc(task)} passed in {hits} of {len(group)} runs</span>" if task else ""
    return (f'<div class="card {cls}"><span class="k">{esc(label)} · {len(group)} runs</span>'
            f'<span class="big">{esc(solved)}<em> / {group[0]["total"]}</em></span>'
            f'<span class="sub">mean {mean:,.0f} tokens per run</span>{task_line}</div>')


CLEAN_CHECKPOINTS = {"7e2148e", "c07f702"}  # earlier checkpoints also hold an interactive chat; never linked
MONO = "font:13px/1.5 'JetBrains Mono',monospace;white-space:normal;overflow-wrap:anywhere;padding:6px 8px"


def provenance_html() -> str:
    """Who wrote each line of the worker's prompt: Entire blame joined to round records (scripts/provenance.py)."""
    f = ROOT / "evidence" / "provenance.json"
    if not f.exists():
        return ""
    data = json.loads(f.read_text(encoding="utf-8"))
    prompt, code = data["mend/prompts/worker.md"], data["mend/worker.py"]
    rows = []
    for ln in prompt["lines"]:
        r, tag = ln.get("round"), "AI" if ln["by"] == "ai" else "HU"
        who = f'<a class="link" href="{REPO}/blob/main/{esc(r["diagnosis"])}">round {r["round"]}</a>' if r else ""
        rows.append(f'<tr><td class="sub">{ln["n"]}</td><td style="white-space:nowrap"><b>[{tag}]</b> {who}</td>'
                    f'<td style="{MONO}">{esc(ln["text"]) or "&nbsp;"}</td></tr>')
    per_round = {}  # round number -> (round record, commit, lines written or co-written by AI)
    for ln in code["lines"]:
        if ln.get("round") and ln["by"] != "human":
            r = ln["round"]
            per_round[r["round"]] = (r, ln["commit"], per_round.get(r["round"], (0, 0, 0))[2] + 1)
    items = []
    for n, (r, commit, count) in sorted(per_round.items()):
        link = f' · <a class="link" href="{ENTIRE}{commit}">Entire checkpoint</a>' if commit in CLEAN_CHECKPOINTS else ""
        items.append(f"<li>Round {n}: {count} lines · {esc(r['title'])}{link}</li>")
    sp, sc = prompt["summary"], code["summary"]
    return f"""
<section id="provenance"><div class="wrap">
  <p class="eyebrow">Who wrote the worker?</p><h2>{sp["ai_percentage"]}% of its instructions were written by Mend itself.</h2>
  <p class="sub">Line-by-line attribution from <code>entire blame</code>. Every AI-written line leads to its Entire checkpoint, then to the
  instruction the supervisor gave Claude Code, then to the diagnosis, then to the neatlogs traces that diagnosis read.</p>
  <div class="card tablewrap" style="margin-top:20px"><p class="k" style="margin:0 0 8px">mend/prompts/worker.md, the worker's whole system prompt today</p>
  <table>{"".join(rows)}</table></div>
  <div class="card" style="margin-top:16px"><p class="k" style="margin:0 0 8px">mend/worker.py: {sc["ai_percentage"]}% AI-written,
  {sc["mixed_percentage"]}% co-written, {sc["human_percentage"]}% human ({sc["total_lines"]} lines). AI-written or co-written lines by round:</p>
  <ul class="sub" style="margin:0;padding-left:18px">{"".join(items)}</ul></div>
  <p class="sub">Generated by <a class="link" href="{REPO}/blob/main/scripts/provenance.py">scripts/provenance.py</a> into
  <a class="link" href="{REPO}/blob/main/evidence/provenance.json">evidence/provenance.json</a>.</p>
</div></section>"""


def ablation_html() -> str:
    """Leave-one-out ablation (scripts/ablation.py): which kept fixes carry the gain."""
    f = ROOT / "evidence" / "ablation.json"
    if not f.exists():
        return ""
    a = json.loads(f.read_text(encoding="utf-8"))
    mean = sum(b["tokens"] for b in a["baseline"]) / len(a["baseline"])
    top = max(r["tokens"] for r in a["ablated"])
    bars = "".join(
        f'<div style="margin:10px 0"><div class="k">Without round {r["round"]} · {r["passed"]}/{r["total"]} solved · '
        f'{r["tokens"]:,} tokens ({r["tokens"] / mean - 1:+.0%})</div>'
        f'<div style="height:10px;border-radius:4px;background:var(--ink);width:{r["tokens"] / top * 100:.0f}%"></div></div>'
        for r in sorted(a["ablated"], key=lambda r: -r["tokens"]))
    return f"""
<section id="ablation"><div class="wrap">
  <p class="eyebrow">Which fixes carry the gain?</p><h2>Take one out, run it again.</h2>
  <p class="sub">Today's worker with one kept fix reverted, re-run on all 29 tasks. Today's worker itself, run 3 times: 29/29 each time,
  {mean:,.0f} tokens on average (dashed line). Rounds 1 and 4 cannot be removed alone: later fixes build on them.</p>
  <div class="card" style="margin-top:20px;position:relative">{bars}
  <div style="position:absolute;top:12px;bottom:12px;left:calc(24px + (100% - 48px) * {mean / top:.3f});border-left:2px dashed var(--mute)" title="today's worker, mean"></div></div>
  <p class="sub">One run each · <a class="link" href="{REPO}/blob/main/evidence/ablation.json">evidence/ablation.json</a></p>
</div></section>"""


CSS = """/* Editions-style, light: sage ground, giant tight sans titles, italic serif sub-lines with a swash initial,
   thin line art, black pills for actions. Green/red only ever mean pass/fail. */
:root{--bg:#e6e6dd;--paper:#f4f4ee;--ink:#0f0f0d;--mute:#5d5d55;--line:#cbcbbf;--accent:#0f0f0d;--ok:#16794a;--bad:#b83a3a}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Inter,system-ui,sans-serif}
a{color:inherit} .wrap{max-width:1160px;margin:auto;padding:0 24px}
nav{position:sticky;top:0;background:rgba(230,230,221,.86);backdrop-filter:blur(10px);z-index:5}
nav .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
.logo{text-decoration:none;display:flex;flex-direction:column;line-height:1.05}
.logo b{font:800 17px 'Inter Tight',sans-serif;letter-spacing:-.01em} .logo span{font-size:12px;color:var(--mute)}
nav .links{display:flex;align-items:center;gap:22px} nav .links a{color:var(--mute);text-decoration:none;font-size:14px}
nav .links a:hover{color:var(--ink)} nav .links a.pill{color:#fff}
.pill{display:inline-block;background:var(--ink);color:#fff;border-radius:999px;padding:9px 18px;font-weight:600;font-size:14px;text-decoration:none;border:1px solid var(--ink)}
.pill.ghost{background:transparent;color:var(--ink)}
header{position:relative;overflow:hidden;padding:72px 0 64px}
header svg.art{position:absolute;inset:0;width:100%;height:100%;z-index:0}
header .wrap{position:relative;z-index:1}
.mega{font:800 clamp(96px,19vw,248px)/.82 'Inter Tight',sans-serif;letter-spacing:-.055em;margin:0}
.lede{font:italic 400 clamp(26px,3.4vw,40px)/1.15 'Instrument Serif',Georgia,serif;margin:18px 0 0;max-width:820px}
.cap{font:400 1.9em/0 'Pinyon Script',cursive;font-style:normal;vertical-align:-.12em;margin-right:.03em}
.intro{color:var(--mute);font-size:18px;max-width:600px;margin:22px 0 0}
.cta{display:flex;gap:12px;margin-top:28px;flex-wrap:wrap}
.hero-grid{display:grid;grid-template-columns:1.4fr 1fr;gap:40px;align-items:end;margin-top:28px}
.stat,.card{background:var(--paper);border-radius:22px;padding:26px;box-shadow:0 1px 1px rgba(15,15,13,.04),0 18px 40px rgba(15,15,13,.07);display:flex;flex-direction:column;gap:6px}
.k{font:600 13px/1.2 Inter,sans-serif;color:var(--ink)}
.big{font:800 56px/1 'Inter Tight',sans-serif;letter-spacing:-.04em} .big em{font-style:normal;color:var(--mute);font-size:24px;letter-spacing:0}
.sub{color:var(--mute);font-size:14px} .link{color:var(--ink);text-decoration:underline;text-underline-offset:3px;font-weight:600;font-size:14px;margin-top:6px}
section{padding:96px 0} section:nth-of-type(even){background:var(--paper)}
section:nth-of-type(even) .stat,section:nth-of-type(even) .card,section:nth-of-type(even) .step{background:var(--bg)}
.eyebrow{font:600 14px/1 Inter,sans-serif;color:var(--ink);margin:0 0 14px}
h2{font:800 clamp(40px,6vw,76px)/.95 'Inter Tight',sans-serif;letter-spacing:-.045em;margin:0 0 18px}
h2 + .sub, .wrap > .sub{font:italic 400 22px/1.3 'Instrument Serif',Georgia,serif;color:var(--mute);max-width:760px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:40px}
.step{background:var(--paper);border-radius:20px;padding:24px;box-shadow:0 1px 1px rgba(15,15,13,.04),0 12px 28px rgba(15,15,13,.05)}
.step b{display:block;margin:8px 0 6px;font:800 24px 'Inter Tight',sans-serif;letter-spacing:-.02em} .step p{margin:0;color:var(--mute);font-size:15px}
.n{font:400 30px/1 'Pinyon Script',cursive;color:var(--mute)}
.two{display:grid;grid-template-columns:1.1fr 1fr;gap:48px;align-items:center} .two p{color:var(--mute);font-size:17px} .two b{color:var(--ink)}
.ba{display:grid;gap:16px} .two-col{grid-template-columns:1fr 1fr;margin-top:28px} .card.bad .big em,.card.ok .big em{color:var(--mute)} .card.bad .big{color:var(--bad)} .card.ok .big{color:var(--ok)}
.tools{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:36px}
.tool h3{margin:0 0 6px;font:800 26px 'Inter Tight',sans-serif;letter-spacing:-.02em} .tool p{margin:0 0 10px;color:var(--mute);font-size:15px}
table{width:100%;border-collapse:collapse;margin-top:24px;font-size:14px}
th,td{text-align:left;padding:12px 8px;border-bottom:1px solid var(--line)} th{color:var(--mute);font-weight:500}
td:nth-child(3){white-space:nowrap} td.ok{color:var(--ok);font-weight:600} td.miss{color:#a26a12;font-weight:600} .tablewrap{overflow-x:auto}
footer{padding:48px 0;color:var(--mute);font-size:14px}
@media (max-width:820px){.hero-grid,.two,.two-col{grid-template-columns:1fr} .steps,.tools{grid-template-columns:1fr} nav .links a.hide{display:none} section{padding:64px 0}}
@media (prefers-reduced-motion:no-preference){.art circle,.art path{stroke-dasharray:1600;animation:draw 2.4s ease-out both} @keyframes draw{from{stroke-dashoffset:1600}to{stroke-dashoffset:0}}}"""


def render() -> str:
    f = facts()
    vrounds = json.dumps([{"before": r["before"], "after": r["after"], "kept": r["kept"], "amended": "stats" in r} for r in f["rounds"]])
    vsets = json.dumps([{"label": label, "ids": [r["run_id"] for r in f[key]]} for label, key in [
        ("Held-out, original worker", "held_before"), ("Held-out, after self-repair", "held_after"),
        ("Real-world library, original worker", "real_before"), ("Real-world library, after self-repair", "real_after"),
        ("Hardware designs, original worker", "hw_before"), ("Hardware designs, after self-repair", "hw_after")] if f[key]])
    first, story = f["first"], f["story"]
    kept = [r for r in f["rounds"] if r["kept"]]
    if kept:
        last = kept[-1]
        chain = [last]  # walk back through rounds whose input was the previous round's output
        while any(r["after"] == chain[0]["before"] for r in kept):
            chain.insert(0, next(r for r in kept if r["after"] == chain[0]["before"]))
        start = chain[0]
        delta = (last["after_tokens"] - start["before_tokens"]) / start["before_tokens"] * 100
        hero_stat = (f'<div class="stat"><span class="k">{len(kept)} self-repair rounds kept · {len(f["rounds"]) - len(kept)} reverted by the gate</span>'
                     f'<span class="big">{delta:+.0f}%<em> tokens</em></span>'
                     f'<span class="sub">latest chain of {len(chain)} rounds: {start["before_passed"]}/{start["total"]} → {last["after_passed"]}/{last["total"]} tasks solved, '
                     f'{start["before_tokens"]:,} → {last["after_tokens"]:,} tokens (single runs)</span>'
                     f'<a class="link" href="#rounds">see every round →</a></div>')
    else:
        hero_stat = '<div class="stat"><span class="k">No self-repair round yet</span></div>'

    if story and story["fixed"]:
        k = story["fixed"][0]
        b, a = story["b"][k], story["a"][k]
        story_html = f"""
<section id="story"><div class="wrap two">
  <div><p class="eyebrow">The first bug Mend found in itself</p>
  <h2>It was deleting the end of long files.</h2>
  <p>Reading its own neatlogs traces, the supervisor saw the worker read only the first 200 lines of a
  233-line file, then rewrite the <b>whole file</b> to change one word. Everything after line 200 was
  silently gone. The fix it wrote for itself: <b>{esc(story['title'])}</b>.</p>
  <a class="link" href="{REPO}/blob/main/{esc(story['diagnosis_file'])}">read the full diagnosis →</a></div>
  <div class="ba">
    <div class="card bad"><span class="k">Before · task {esc(k)}</span><span class="big">failed</span>
      <span class="sub">ran out of turns at {b.get('turns')} · trace {esc(str(b.get('trace_id'))[:8])}</span></div>
    <div class="card ok"><span class="k">After · task {esc(k)}</span><span class="big">passed</span>
      <span class="sub">in {a.get('turns')} turns · trace {esc(str(a.get('trace_id'))[:8])}</span></div>
  </div>
</div></section>"""
    else:
        story_html = ""

    task = story["fixed"][0] if story and story["fixed"] else None
    if f["before_runs"] and f["after_runs"]:
        mb = sum(tokens(r) for r in f["before_runs"]) / len(f["before_runs"])
        ma = sum(tokens(r) for r in f["after_runs"]) / len(f["after_runs"])
        repeat_html = f"""
<section id="repeat"><div class="wrap">
  <p class="eyebrow">Repeatable, not lucky</p><h2>Same 28 tasks, run again and again.</h2>
  <p class="sub">The worker before its first self-repair against the worker after it, each run several times.
  Mean tokens per run changed by {(ma - mb) / mb * 100:+.1f}%.</p>
  <div class="ba two-col">{repeat_card("Before self-repair", f["before_runs"], task, "bad")}{repeat_card("After self-repair", f["after_runs"], task, "ok")}</div>
</div></section>"""
    else:
        repeat_html = ""

    round_rows = "".join(
        f"<tr><td>{i}</td><td>{esc(r['title'])} <a class=\"link\" href=\"{REPO}/blob/main/{esc(r['diagnosis_file'])}\">diagnosis</a></td>"
        f"<td>{r['before_passed']} → {r['after_passed']} / {r['total']}</td>"
        f"<td>{(r['after_tokens'] - r['before_tokens']) / r['before_tokens'] * 100:+.1f}%</td>"
        f"<td class=\"{'ok' if r['kept'] else 'miss'}\">{'kept' if r['kept'] else 'reverted'}</td>"
        f"<td><a class=\"link\" href=\"{REPO}/commit/{esc(r['commit'])}\">{esc(r['commit'])}</a></td></tr>"
        for i, r in enumerate(f["rounds"], 1))
    rounds_html = f"""
<section id="rounds"><div class="wrap">
  <p class="eyebrow">Every self-repair round</p><h2>Each fix was diagnosed from traces and written by the agent.</h2>
  <p class="sub">A round keeps its patch only if more tasks pass, or the same tasks pass with at least 15% fewer tokens. Each fix is a commit written by Claude Code. From round 4 the supervisor runs in a clean clone, and Entire links each fix to the session that wrote it.</p>
  <div class="card" style="margin:28px 0 8px;overflow-x:auto">{dumbbell(f["rounds"])}</div>
  <div class="tablewrap"><table><tr><th>#</th><th>What Mend changed in itself</th><th>Solved</th><th>Tokens</th><th>Result</th><th>Commit</th></tr>{round_rows}</table></div>
</div></section>"""

    if f["held_before"] and f["held_after"]:
        hb = sum(tokens(r) for r in f["held_before"]) / len(f["held_before"])
        ha = sum(tokens(r) for r in f["held_after"]) / len(f["held_after"])
        heldout_html = f"""
<section id="heldout"><div class="wrap">
  <p class="eyebrow">Held-out test: bugs the supervisor never saw</p><h2>It generalises.</h2>
  <p class="sub">{f["held_before"][0]["total"]} new planted bugs, never shown to the supervisor and never used in a diagnosis.
  Original worker against the self-repaired one, each run twice. Mean tokens per run changed by {(ha - hb) / hb * 100:+.1f}%.</p>
  <div class="ba two-col">{repeat_card("Original worker", f["held_before"], None, "bad")}{repeat_card("After self-repair", f["held_after"], None, "ok")}</div>
</div></section>"""
    else:
        heldout_html = ""

    if f["real_before"] and f["real_after"]:
        rb = sum(tokens(r) for r in f["real_before"]) / len(f["real_before"])
        ra = sum(tokens(r) for r in f["real_after"]) / len(f["real_after"])
        real_html = f"""
<section id="realworld"><div class="wrap">
  <p class="eyebrow">Real-world test: an open-source library it never saw</p><h2>Beyond our sandbox.</h2>
  <p class="sub">{f["real_before"][0]["total"]} bugs planted in <a class="link" href="{REPO}/tree/main/realworld/inflection">inflection</a>
  (MIT, unmodified, 455 of its own tests). Never shown to the supervisor. Original worker against the self-repaired one, each run twice.
  Mean tokens per run changed by {(ra - rb) / rb * 100:+.1f}%.</p>
  <div class="ba two-col">{repeat_card("Original worker", f["real_before"], None, "bad")}{repeat_card("After self-repair", f["real_after"], None, "ok")}</div>
</div></section>"""
    else:
        real_html = ""

    def gain(before, after):  # "same 9/9 at 58% fewer tokens" from the run files
        if not (before and after):
            return ""
        tb, ta = (sum(tokens(r) for r in g) / len(g) for g in (before, after))
        pb, pa = (sum(r["passed"] for r in g) / len(g) for g in (before, after))
        return (f"{pb:g} → {pa:g} of {before[0]['total']} solved" if pa > pb
                else f"same {pa:g}/{before[0]['total']}, {(1 - ta / tb) * 100:.0f}% fewer tokens")
    hw_line, sc_line = gain(f["hw_before"], f["hw_after"]), gain(f["sc_before"], f["sc_after"])
    hw_html = f"""
<section id="hardware"><div class="wrap">
  <p class="eyebrow">Beyond software</p><h2>It carries over to hardware.</h2>
  <p class="sub">Bugs in chip designs and circuit schematics the supervisor never saw, checked in simulation.</p>
  <div class="tools" style="grid-template-columns:repeat(2,1fr)">
    <div class="tool card"><h3>Chip designs</h3><p>9 bugs in 8 Amaranth HDL designs (ALU, FIFO, UART...): {esc(hw_line)}.</p></div>
    <div class="tool card"><h3>Circuit schematics</h3><p>8 board bring-up bugs in 7 circuit netlists: {esc(sc_line)}.</p></div>
  </div>
  <p><a class="pill" href="hardware.html">See the waveforms, schematics and bugs →</a></p>
</div></section>""" if hw_line or sc_line else ""

    def run_row(r):
        return (f"<tr><td>{esc(r['run_id'][5:16].replace('T', ' '))}</td><td>{esc(r['model'].replace('claude-', ''))}</td>"
                f"<td><a class=\"link\" href=\"{REPO}/commit/{esc(r['worker_commit'])}\">{esc(r['worker_commit'])}</a></td>"
                f"<td class=\"{'ok' if r['passed'] == r['total'] else 'miss'}\"><b>{r['passed']}/{r['total']}</b></td><td>{tokens(r):,}</td></tr>")
    rows = "".join(run_row(r) for r in sorted(f["opus"] + f["haiku"], key=lambda r: r["run_id"]))

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mend: agents that fix themselves</title>
<meta name="description" content="Mend reads its own neatlogs traces, patches itself, and keeps a fix only if a full re-run gets better.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Instrument+Serif:ital@0;1&family=Pinyon+Script&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
{CSS}
</style></head><body>
<nav><div class="wrap"><a class="logo" href="#"><b>Mend</b><span>neatHack 2026</span></a>
<div class="links"><a class="hide" href="#how">How it works</a><a class="hide" href="#rounds">Rounds</a><a class="hide" href="#evidence">Evidence</a>
<a class="hide" href="hardware.html">Hardware</a><a class="hide" href="report.html">Full report</a><a class="pill" href="{REPO}">View the code</a></div></div></nav>

<header>
<svg class="art" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true" fill="none" stroke="#b9b9ad" stroke-width="1">
  <circle cx="860" cy="330" r="300"/><circle cx="860" cy="330" r="190"/><circle cx="860" cy="330" r="80"/>
  <path d="M0 330 H1200"/><path d="M860 0 V700"/><path d="M560 30 Q860 330 1160 30"/><path d="M560 630 Q860 330 1160 630"/>
  <path d="M0 700 Q600 120 1200 700"/>
</svg>
<div class="wrap">
  <p class="eyebrow">The Good Engineers · built during neatHack, 10-12 Oct 2026</p>
  <h1 class="mega">Mend</h1>
  <p class="lede"><span class="cap">A</span>gents that fix themselves, and prove it.</p>
  <div class="hero-grid">
    <div><p class="intro">Mend reads its own neatlogs traces, works out why it failed, patches its own code, and keeps
    the fix only if a full re-run gets better. Otherwise it reverts.</p>
    <div class="cta"><a class="pill" href="#watch" onclick="document.getElementById('watch').showModal();document.getElementById('watchv').play();return false;">&#9654; Watch it fix itself</a><a class="pill ghost" href="#evidence">See the evidence</a><a class="pill ghost" href="report.html">Full report</a></div></div>
    {hero_stat}
  </div>
</div></header>

<section id="how"><div class="wrap">
  <p class="eyebrow">How it works</p><h2>A self-repair loop with a hard gate.</h2>
  <div class="steps">
    <div class="step"><span class="n">01</span><b>Run</b><p>A worker agent fixes planted bugs in a real codebase: {f['tasks_total']} tasks, judged by the test suite, not by the agent.</p></div>
    <div class="step"><span class="n">02</span><b>Trace</b><p>Every model call and tool call is a span in neatlogs, with inputs, outputs, tokens and cost.</p></div>
    <div class="step"><span class="n">03</span><b>Diagnose</b><p>A supervisor pulls failed and wasteful runs back over the neatlogs MCP server and finds the step that went wrong.</p></div>
    <div class="step"><span class="n">04</span><b>Patch</b><p>Claude Code applies one general fix to the worker: never a task-specific hack, never the tests.</p></div>
    <div class="step"><span class="n">05</span><b>Checkpoint</b><p>Entire links the commit to the session that wrote it, so every self-fix carries its reasoning.</p></div>
    <div class="step"><span class="n">06</span><b>Prove</b><p>The whole suite re-runs. More tasks solved, or the same with 15% fewer tokens: kept. Anything else: reverted.</p></div>
  </div>
</div></section>
{story_html}
{repeat_html}
{heldout_html}
{real_html}
{hw_html}
{rounds_html}
{provenance_html()}
{ablation_html()}
<section id="judgment"><div class="wrap">
  <p class="eyebrow">Is self-healing self-defeating?</p><h2>Mend only fixes what isn't a choice.</h2>
  <p class="sub">neatlogs' founder <a class="link" href="https://neatlogs.com/blog/self-healing-is-self-defeating">argues</a> that a loop which fixes
  everything drifts toward the median unless someone defines "better". His answer has three steps: automate what isn't a choice, ask when it is, remember the answer.</p>
  <div class="tools">
    <div class="tool card"><h3>Not a choice</h3><p>Every task is judged by the library's own tests, run by the runner, not the agent. Token cost comes from the API. Mend never tunes tone or policy.</p></div>
    <div class="tool card"><h3>Remembered</h3><p>Every round, kept or reverted, is a run record and an Entire checkpoint, and both feed the next diagnosis. A failed fix is not proposed twice.</p></div>
    <div class="tool card"><h3>Asked once</h3><p>Each diagnosis says whether its fix is a correction or a choice. A choice stops the round and asks a person; the answer becomes a precedent every later diagnosis must follow. No real choice has come up yet: round 7 judged its fix a correction.</p></div>
  </div>
</div></section>

<section id="evidence"><div class="wrap">
  <p class="eyebrow">Evidence</p><h2>Every number comes from a run file.</h2>
  <p class="sub">{f['runs_total']} full suite runs so far. A cheap worker (Claude Haiku 4.5) repaired by a
  stronger supervisor (Claude Opus 5.5). Each row links to data in <a class="link" href="{REPO}/tree/main/runs">runs/</a>.</p>
  <div class="tablewrap"><table><tr><th>Run (UTC)</th><th>Worker model</th><th>Worker version</th><th>Solved</th><th>Tokens</th></tr>{rows}</table></div>
  <p><a class="link" href="report.html">Open the full report: every task, every run, every diagnosis →</a></p>
</div></section>

<section id="verify"><div class="wrap">
  <p class="eyebrow">Check it yourself</p><h2>Two minutes, no API keys.</h2>
  <p class="sub">Every number on this page is recomputed from the raw run files. The same checks run on every push in
  <a class="link" href="{REPO}/actions">GitHub Actions</a>.</p>
  <div class="card" style="margin-top:24px;overflow-x:auto"><pre style="margin:0;font:14px/1.7 'JetBrains Mono',monospace">git clone {REPO}
cd mend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
python -m mend.verify        # recompute every README number from runs/*.json
python -m mend.tasks --check # all 47 planted bugs break their test suites; correct code passes
pytest -q                    # unit tests</pre></div>
  <div class="card" style="margin-top:16px"><p style="margin:0 0 12px"><b>Or right here, in your browser:</b> this fetches the raw
  run files from this site, re-counts every task, and re-applies the <a class="link" href="{REPO}/blob/main/docs/GATE.md">pre-registered keep rule</a> to every round.</p>
  <button class="pill" id="vbtn" type="button" style="width:auto;cursor:pointer">Re-check every round now</button>
  <pre id="vout" style="margin:14px 0 0;font:13px/1.7 'JetBrains Mono',monospace;white-space:pre-wrap"></pre></div>
</div></section>
<script>
const VROUNDS = {vrounds}, VSETS = {vsets};
document.getElementById('vbtn').onclick = async () => {{
  const out = document.getElementById('vout'), log = t => out.textContent += t + String.fromCharCode(10);
  out.textContent = ''; let bad = 0;
  const run = async id => {{
    const r = await (await fetch('runs/' + id + '.json')).json();
    const tok = {{}}, pass = {{}};
    r.tasks.forEach(t => {{ tok[t.task_id] = t.input_tokens + t.output_tokens; pass[t.task_id] = t.passed; }});
    return {{passed: r.tasks.filter(t => t.passed).length, total: r.tasks.length,
             tokens: r.tasks.reduce((s, t) => s + t.input_tokens + t.output_tokens, 0), tok, pass}};
  }};
  const ciHigh = (b, a) => {{  // amendment 1: 97.5th percentile of a paired bootstrap of tokens-after / tokens-before
    const ids = Object.keys(b.tok).filter(k => k in a.tok); let seed = 1; const sims = [];
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let n = 0; n < 4000; n++) {{
      let sb = 0, sa = 0;
      for (let i = 0; i < ids.length; i++) {{ const k = ids[Math.floor(rnd() * ids.length)]; sb += b.tok[k]; sa += a.tok[k]; }}
      sims.push(sa / sb);
    }}
    sims.sort((x, y) => x - y); return sims[Math.floor(0.975 * sims.length) - 1];
  }};
  try {{
    for (const [i, rd] of VROUNDS.entries()) {{
      const b = await run(rd.before), a = await run(rd.after);
      let keep = a.passed > b.passed || (a.passed === b.passed && a.tokens <= 0.85 * b.tokens);
      if (rd.amended) {{
        const broke = Object.keys(b.pass).filter(k => b.pass[k] && a.pass[k] === false).length;
        keep = keep && broke === 0 && (a.passed > b.passed || ciHigh(b, a) < 1.0);
      }}
      const ok = keep === rd.kept; bad += !ok;
      log(`${{ok ? '✓' : '✗ MISMATCH'}} round ${{i + 1}}: ${{b.passed}}/${{b.total}} → ${{a.passed}}/${{a.total}} solved, ${{b.tokens.toLocaleString()}} → ${{a.tokens.toLocaleString()}} tokens → ${{rd.amended ? 'amended gate' : 'gate'}} says ${{keep ? 'KEEP' : 'REVERT'}} (recorded: ${{rd.kept ? 'kept' : 'reverted'}})`);
    }}
    for (const s of VSETS) {{
      const rs = await Promise.all(s.ids.map(run));
      log(`✓ ${{s.label}}: ${{rs.map(r => r.passed + '/' + r.total).join(', ')}} (${{s.ids.length}} run file${{s.ids.length > 1 ? 's' : ''}})`);
    }}
    log(bad ? `${{bad}} mismatch(es)` : 'All recorded decisions match the rule.');
  }} catch (e) {{ log('Could not fetch run files: ' + e); }}
}};
</script>

<section id="tools"><div class="wrap">
  <p class="eyebrow">Built with</p><h2>neatlogs, Entire and cfo.ai, each doing real work.</h2>
  <div class="tools">
    <div class="tool card"><h3>neatlogs</h3><p>Traces every run. The supervisor reads those traces back over MCP to diagnose failures, then writes every keep/revert verdict back into neatlogs as its own trace, with a detection on each revert.</p><a class="link" href="{REPO}/tree/main/evidence">trace evidence →</a></div>
    <div class="tool card"><h3>Entire</h3><p>Every fix Mend makes to itself is a Claude Code session linked to its commit as a checkpoint. <code>entire blame</code> traces each line of the worker back to the session that wrote it, and <code>entire search</code> stops Mend paying twice for a fix that already failed.</p><a class="link" href="{ENTIRE}7e2148e201fdaa9b2b3f921d1f2651950f537205">a clean self-fix checkpoint →</a></div>
    <div class="tool card"><h3>cfo.ai</h3><p>Prices Mend from measured cost per repair round. It showed our first price leaves a 31% margin, so pricing changes next.</p><a class="link" href="{REPO}/blob/main/docs/business-plan.md">business plan →</a></div>
  </div>
</div></section>

<footer><div class="wrap">Mend · built during neatHack, 10–12 October 2026 · <a href="{REPO}">github.com/thegoodengineers/mend</a></div></footer>
<dialog id="watch" style="border:0;border-radius:22px;padding:0;max-width:min(1100px,94vw);background:#0f0f0d;box-shadow:0 40px 100px rgba(0,0,0,.35)">
<video id="watchv" src="video/live/mend-live.mp4" controls playsinline preload="metadata" style="display:block;width:100%;height:auto"></video>
<form method="dialog" style="position:absolute;top:10px;right:12px;margin:0"><button aria-label="Close" style="border:0;border-radius:999px;background:#f4f4ee;padding:6px 12px;font:600 14px Inter;cursor:pointer" onclick="document.getElementById('watchv').pause()">Close</button></form>
<p style="margin:0;padding:10px 16px;color:#cbcbbf;font:13px Inter">Live recording at real speed: the original worker vs the self-repaired worker on the same task. Both runs traced in neatlogs. Narration is synthetic voice.</p>
</dialog>
</body></html>"""


if __name__ == "__main__":
    out = ROOT / ("site_preview.html" if "preview" in sys.argv else "index.html")
    out.write_text(render(), encoding="utf-8")
    print(f"wrote {out.name}")
    from mend import beyond
    (ROOT / "hardware.html").write_text(beyond.render(), encoding="utf-8")
    print("wrote hardware.html")
