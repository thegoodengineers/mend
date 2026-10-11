"""Build report.html from runs/*.json: rounds, per-task results across runs, diagnoses.

    python -m mend.report    # writes report.html (static, no server)
"""

import html
import json
import re

from mend.tasks import ROOT, load_tasks

RUNS = ROOT / "runs"
REPO = "https://github.com/thegoodengineers/mend"
OUT = ROOT / "report.html"


def esc(value) -> str:
    return html.escape(str(value))


def load_runs() -> list[dict]:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUNS.glob("*.json")) if "." not in p.stem]
    return [r for r in runs if r.get("tasks")]


def load_rounds() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUNS.glob("*.round.json"))]


# Commits whose Entire checkpoint is published (from the clean runner clone; earlier ones were removed).
CHECKPOINTED = {"7e2148e", "c07f702"}


def commit_links(sha: str) -> str:
    link = f'<a href="{REPO}/commit/{esc(sha)}">{esc(sha)}</a>'
    if sha[:7] in CHECKPOINTED:
        link += f' · <a href="https://entire.io/gh/thegoodengineers/mend/commit/{esc(sha)}">Entire checkpoint</a>'
    return link


def hero_html(rounds: list[dict]) -> str:
    if not rounds:
        return ""
    first = rounds[0]
    last = rounds[-1]
    tok_before = first.get("before_tokens", 0)
    tok_after = last.get("after_tokens", 0)
    tok_pct = f"−{100 - round(tok_after / tok_before * 100)}%" if tok_before else ""
    return (
        f'<section class="hero">'
        f'<p class="hero-label">Latest self-repair result</p>'
        f'<div class="hero-score">'
        f'<span class="score-before">{first["before_passed"]}<span class="score-denom">/{first["total"]}</span></span>'
        f'<span class="arrow">→</span>'
        f'<span class="score-after">{last["after_passed"]}<span class="score-denom">/{last["total"]}</span></span>'
        f'</div>'
        f'<p class="hero-sub">tasks solved &nbsp;·&nbsp; {tok_before:,} → {tok_after:,} tokens&nbsp;<b>{tok_pct}</b>'
        f'&nbsp;·&nbsp; {len(rounds)} self-repair round{"s" if len(rounds) != 1 else ""} kept</p>'
        f'</section>'
    )


def _demo_data(rounds: list[dict], runs: list[dict], tasks: list[dict]) -> str:
    """Return a JSON string of the data needed by the demo overlay."""
    if not rounds:
        return "null"
    r = rounds[0]
    before_run = next((x for x in runs if x["run_id"] == r["before"]), None)
    after_run = next((x for x in runs if x["run_id"] == r["after"]), None)
    failing_task_id = None
    failing_task_report = ""
    if before_run and after_run:
        for t in tasks:
            b = next((x for x in before_run["tasks"] if x["task_id"] == t["id"]), None)
            a = next((x for x in after_run["tasks"] if x["task_id"] == t["id"]), None)
            if b and a and not b["passed"] and a["passed"]:
                failing_task_id = t["id"]
                failing_task_report = t.get("report", "")
                break
    diag_text, title = "", r.get("title", "")
    diag_rel = r["diagnosis"].replace("\\", "/")  # the round record names its diagnosis file
    diag_path = ROOT / diag_rel
    if diag_path.exists():
        text = diag_path.read_text(encoding="utf-8")
        row = re.search(rf"^\| {re.escape(str(failing_task_id))} \| ([^|]+)\| ([^|]+)\|", text, re.M)
        if row:
            diag_text = f"Failing step: {row.group(1).strip()}\n\nCause: {row.group(2).strip()}"
        if not title:
            m = re.search(r"## Chosen fix: (.+)", text)
            title = m.group(1) if m else ""
    sha = r["commit"]
    checkpoint_url = f"https://entire.io/gh/thegoodengineers/mend/commit/{sha}" if sha[:7] in CHECKPOINTED else ""
    return json.dumps({
        "before_passed": r["before_passed"],
        "after_passed": r["after_passed"],
        "total": r["total"],
        "commit": sha,
        "commit_url": f"{REPO}/commit/{sha}",
        "checkpoint_url": checkpoint_url,
        "failing_task": failing_task_id,
        "failing_task_report": failing_task_report,
        "diagnosis": diag_text,
        "diagnosis_url": f"{REPO}/blob/main/{diag_rel}",
        "title": title,
    }, ensure_ascii=False).replace("</", "<\\/")  # never close the <script> it is embedded in


DEMO_SCRIPT = r"""
<div id="demo" aria-live="polite" aria-atomic="true" style="display:none;position:fixed;inset:0;background:var(--bg);z-index:100;overflow:hidden"></div>
<script>
(function(){
  if(!/[?&]demo=1/.test(location.search))return;
  var d=document.getElementById('demo');
  d.style.display='block';
  var DATA=__DEMO_DATA__;
  if(!DATA){d.innerHTML='<p style="padding:40px">No round data yet.</p>';return;}
  var reduced=matchMedia('(prefers-reduced-motion:reduce)').matches;
  var DELAY=reduced?600:3000;
  var steps=[
    function(){
      d.innerHTML='<div class="ds"><p class="dl">Step 1 of 4 — Failing task</p>'
        +'<h2 class="dt">'+DATA.failing_task+' <span class="bad-tag">FAIL</span></h2>'
        +'<p class="dd">'+escHtml(DATA.failing_task_report)+'</p></div>';
    },
    function(){
      d.innerHTML='<div class="ds"><p class="dl">Step 2 of 4 — Diagnosis</p>'
        +'<h2 class="dt">Supervisor reads the trace</h2>'
        +'<pre class="dpre">'+escHtml(DATA.diagnosis)+'</pre>'
        +'<p class="dd"><a href="'+DATA.diagnosis_url+'" target="_blank">full diagnosis ↗</a></p></div>';
    },
    function(){
      var cp=DATA.checkpoint_url?'<a href="'+DATA.checkpoint_url+'" target="_blank">Entire checkpoint ↗</a> · ':'';
      d.innerHTML='<div class="ds"><p class="dl">Step 3 of 4 — Patch applied</p>'
        +'<h2 class="dt" style="font-size:clamp(26px,4vw,44px)">'+escHtml(DATA.title||'Fix committed')+'</h2>'
        +'<p class="dd">'+cp+'<a href="'+DATA.commit_url+'" target="_blank">commit '+escHtml(DATA.commit.slice(0,7))+'</a></p></div>';
    },
    function(){
      d.innerHTML='<div class="ds"><p class="dl">Step 4 of 4 — Verified</p>'
        +'<h2 class="dt"><span class="score-b">'+DATA.before_passed+'/'+DATA.total+'</span>'
        +' &rarr; <span class="score-a">'+DATA.after_passed+'/'+DATA.total+'</span></h2>'
        +'<p class="dd">Tasks solved after self-repair</p>'
        +'<p style="margin-top:32px"><a href="?" class="btn">View full report</a></p></div>';
    }
  ];
  var i=0;
  function next(){if(i<steps.length){steps[i]();i++;if(i<steps.length)setTimeout(next,DELAY);}}
  next();
  function escHtml(s){var e=document.createElement('div');e.textContent=s;return e.innerHTML;}
})();
</script>
<style>
#demo .ds{display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;padding:40px;text-align:center;max-width:800px;margin:auto}
#demo .dl{font:500 13px Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:0 0 16px}
#demo .dt{font:800 clamp(32px,6vw,60px)/.95 'Inter Tight',sans-serif;letter-spacing:-.03em;margin:0 0 20px}
#demo .dd{color:var(--mute);font-size:17px;margin:0}
#demo .dpre{text-align:left;white-space:pre-wrap;font-size:13px;background:var(--card);border-radius:12px;padding:16px;max-height:50vh;overflow-y:auto;width:100%}
#demo .bad-tag{color:var(--bad);font-size:.6em;vertical-align:middle;margin-left:8px}
#demo .score-b{color:var(--bad);font-size:1.2em}
#demo .score-a{color:var(--ok);font-size:1.2em}
#demo .btn{display:inline-block;margin-top:8px;padding:12px 28px;background:var(--ink);color:var(--bg);border-radius:99px;text-decoration:none;font-weight:600;font-size:15px}
</style>
"""


def render() -> str:
    runs, rounds = load_runs(), load_rounds()
    tasks = load_tasks()
    round_rows = "".join(
        f"<tr><td>{esc(r['before'])}</td><td>{r['before_passed']}/{r['total']}</td>"
        f"<td>{esc(r['after'])}</td><td>{r['after_passed']}/{r['total']}</td>"
        f"<td>{r.get('before_tokens', 0):,} → {r.get('after_tokens', 0):,}</td>"
        f"<td class=\"{'ok' if r['kept'] else 'bad'}\">{'kept' if r['kept'] else 'reverted'}</td>"
        f"<td>{commit_links(r['commit'])}</td></tr>"
        for r in rounds
    ) or '<tr><td colspan="7">No self-repair rounds yet.</td></tr>'

    head = "".join(f"<th title=\"{esc(r['run_id'])}\">{esc(r['run_id'][5:16])}<br><small>{esc(r['model'].replace('claude-', ''))}</small></th>" for r in runs)
    grid = []
    for t in tasks:
        cells = []
        for r in runs:
            res = next((x for x in r["tasks"] if x["task_id"] == t["id"]), None)
            if res is None:
                cells.append('<td class="na">-</td>')
                continue
            tip = f"turns {res.get('turns')}, stop {res.get('stop')}, trace {res.get('trace_id')}"
            cells.append(f"<td class=\"{'ok' if res['passed'] else 'bad'}\" title=\"{esc(tip)}\">"
                         f"{'pass' if res['passed'] else 'fail'}<small>{res.get('turns', '')}</small></td>")
        grid.append(f"<tr><th class=\"task\" title=\"{esc(t['report'])}\">{esc(t['id'])} <small>{esc(t['difficulty'])}</small></th>{''.join(cells)}</tr>")
    totals = "".join(f"<td><b>{r['passed']}/{r['total']}</b><br><small>{(r.get('input_tokens', 0) + r.get('output_tokens', 0)):,} tok</small></td>" for r in runs)

    diagnoses = "".join(
        f"<details><summary>{esc(p.stem.replace('.diagnosis', ''))}</summary>"
        f"<div class='diag-body'><pre>{esc(p.read_text(encoding='utf-8'))}</pre></div></details>"
        for p in sorted(RUNS.glob("*.diagnosis.md"))
    )
    demo_json = _demo_data(rounds, runs, tasks)
    demo_html = DEMO_SCRIPT.replace("__DEMO_DATA__", demo_json)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Mend report</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@800&family=Instrument+Serif:ital@1&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#e6e6dd;--card:#f4f4ee;--ink:#0f0f0d;--mute:#5d5d55;--line:#cbcbbf;--ok:#16794a;--bad:#b83a3a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Inter,system-ui,sans-serif}}
nav{{position:sticky;top:0;background:rgba(230,230,221,.88);backdrop-filter:blur(10px);z-index:5}}
nav div{{max-width:1160px;margin:auto;padding:0 24px;height:60px;display:flex;align-items:center;justify-content:space-between}}
nav a{{text-decoration:none;color:var(--mute);font-size:14px;margin-left:20px}} nav b{{font:800 17px 'Inter Tight',sans-serif;color:var(--ink)}}
main{{max-width:1160px;margin:auto;padding:40px 24px 64px}}
h1{{margin:0;font:800 clamp(36px,6vw,80px)/.95 'Inter Tight',sans-serif;letter-spacing:-.045em}}
p.sub{{font:italic 400 20px/1.3 'Instrument Serif',Georgia,serif;color:var(--mute);margin:12px 0 32px;max-width:780px}}
section{{background:var(--card);border-radius:22px;padding:24px;margin-bottom:22px;overflow-x:auto;box-shadow:0 1px 1px rgba(15,15,13,.04),0 14px 32px rgba(15,15,13,.06)}}
section.hero{{overflow:visible;text-align:center;padding:40px 24px}}
.hero-label{{font:500 13px Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:0 0 16px}}
.hero-score{{display:flex;align-items:baseline;justify-content:center;gap:20px;margin-bottom:12px}}
.score-before{{font:800 clamp(56px,10vw,96px)/.9 'Inter Tight',sans-serif;color:var(--bad)}}
.score-after{{font:800 clamp(56px,10vw,96px)/.9 'Inter Tight',sans-serif;color:var(--ok)}}
.score-denom{{font-size:.45em;color:var(--mute)}}
.arrow{{font:800 clamp(32px,5vw,56px)/.9 'Inter Tight',sans-serif;color:var(--mute)}}
.hero-sub{{color:var(--mute);font-size:15px;margin:0}}
h2{{font:800 22px 'Inter Tight',sans-serif;letter-spacing:-.02em;margin:0 0 14px}} table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;white-space:nowrap}} th{{color:var(--mute);font-weight:500}}
td.ok{{color:var(--ok);font-weight:600}} td.bad{{color:var(--bad);font-weight:600}} td.na{{color:var(--mute)}}
small{{color:var(--mute);margin-left:6px;font:400 13px Inter,sans-serif;letter-spacing:0}} a{{color:var(--ink);text-underline-offset:3px}}
pre{{white-space:pre-wrap;color:var(--ink);font-size:13px;background:var(--bg);border-radius:12px;padding:14px;overflow-x:auto}}
details{{border-bottom:1px solid var(--line);padding:4px 0}} details:last-child{{border:none}}
summary{{cursor:pointer;padding:10px 0;font-weight:600;font-size:14px;list-style:none;display:flex;align-items:center;gap:8px}}
summary::before{{content:'▶';font-size:11px;color:var(--mute);transition:transform .15s}} details[open] summary::before{{transform:rotate(90deg)}}
.diag-body{{padding:4px 0 12px}}
@media(max-width:600px){{
  main{{padding:24px 16px 48px}}
  section{{padding:18px 14px;border-radius:16px}}
  th,td{{padding:6px 8px;font-size:13px}}
  .hero-score{{gap:12px}}
}}
</style></head><body>
{demo_html}
<nav><div><a href="index.html" style="margin:0"><b>Mend</b></a><span><a href="index.html">Home</a><a href="{REPO}">GitHub</a></span></div></nav>
<main>
<h1>Full report</h1>
<p class="sub">Every round, every task, every run, every diagnosis — generated from the files in <a href="{REPO}/tree/main/runs">runs/</a>.</p>
{hero_html(rounds)}
<section><h2>Self-repair rounds</h2><table><tr><th>Before</th><th>Passed</th><th>After</th><th>Passed</th><th>Tokens</th><th>Result</th><th>Patch</th></tr>{round_rows}</table></section>
<section><h2>Tasks across runs <small>(pass/fail · turns · hover for trace id)</small></h2><table><tr><th>Task</th>{head}</tr>{''.join(grid)}<tr><th>Total</th>{totals}</tr></table></section>
<section><h2>Diagnoses</h2>{diagnoses or '<p style="color:var(--mute)">None yet.</p>'}</section>
</main></body></html>"""


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
