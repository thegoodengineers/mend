"""Build circuit.html: an explorer for the sensor circuit, at schematic level. Left: the bring-up bugs and the agent's
log for the selected one. Right: the netlist as a graph or a table, with the parts that bug touched lit.

    python -m mend.explorer   (also run by `python -m mend.site`)

Data: schematics/circuits/board.cir (parts, nets, blocks), tasks/board.json (bugs) and
evidence/board-agent-logs.json (scripts/board_logs.py: the repaired worker's tool calls read back from neatlogs).
"""

import html
import json
import math
import random

from mend.circuit_art import CSS as ART_CSS, art_svg
from mend.report import REPO
from mend.site import CSS
from mend.tasks import BOARD_FILE, ROOT, load_tasks

NETLIST = ROOT / "schematics" / "circuits" / "board.cir"
COLORS = ["#2f6fd6", "#e07a2e", "#16a07a", "#d6a019", "#d94c86", "#5b4bc4", "#3a8f3a"]
# Bugs whose passing fix is not a real-board fix (from reading the agent's edits; see the README).
CAVEATS = {"BD04": "This fix passes every check but is not a real-board fix: instead of reconnecting the op-amp's feedback, "
                   "the agent set the op-amp model's gain to 1. In simulation that is an ideal buffer; a real op-amp can't be "
                   "changed that way. Tests can be satisfied without fixing the board."}


def parse_netlist():
    """(name, nets, value, block) for each part; block = the '* --- Block ---' heading above it."""
    parts, block = [], "Board"
    for raw in NETLIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("* ---"):
            block = line.strip("*- ").split(":")[0].split("(")[0].split(" to the ")[0].strip()
            continue
        code = line.split("*", 1)[0].split()
        if not code:
            continue
        kind = code[0][0].upper()
        nets = code[1:5] if kind == "E" else code[1:3]
        value = " ".join(code[5:] if kind == "E" else code[3:])
        parts.append({"name": code[0], "nets": nets, "value": value, "block": block,
                      "note": raw.split("*", 1)[1].strip() if "*" in raw else ""})
    return parts


def layout(parts, seed=7):
    """Deterministic spring layout (Fruchterman-Reingold) of parts and nets."""
    nodes = [p["name"] for p in parts] + sorted({n for p in parts for n in p["nets"]})
    edges = [(p["name"], n) for p in parts for n in p["nets"]]
    rnd = random.Random(seed)
    pos = {n: [rnd.uniform(-1, 1), rnd.uniform(-1, 1)] for n in nodes}
    k = math.sqrt(4.0 / len(nodes))
    for step in range(400):
        disp = {n: [0.0, 0.0] for n in nodes}
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = max(math.hypot(dx, dy), 1e-3)
                f = k * k / d
                disp[a][0] += dx / d * f; disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f; disp[b][1] -= dy / d * f
        for a, b in edges:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = max(math.hypot(dx, dy), 1e-3)
            f = d * d / k
            disp[a][0] -= dx / d * f; disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f; disp[b][1] += dy / d * f
        t = 0.1 * (1 - step / 400) + 0.002
        for n in nodes:
            dx, dy = disp[n]
            d = max(math.hypot(dx, dy), 1e-9)
            pos[n][0] += dx / d * min(d, t); pos[n][1] += dy / d * min(d, t)
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    sx, sy = 760 / (max(xs) - min(xs)), 470 / (max(ys) - min(ys))
    return {n: (40 + (x - min(xs)) * sx, 40 + (y - min(ys)) * sy) for n, (x, y) in pos.items()}, edges


def graph_svg(parts, blocks):
    pos, edges = layout(parts)
    color = {p["name"]: COLORS[blocks.index(p["block"]) % len(COLORS)] for p in parts}
    out = ['<svg class="graph" viewBox="0 0 840 550" role="img" aria-label="Netlist graph of the sensor board">']
    for a, b in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        out.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#bdbdb2" stroke-width="1"/>')
    for n, (x, y) in pos.items():
        if n in color:
            out.append(f'<g class="gnode" data-part="{n}"><circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{color[n]}"/>'
                       f'<text x="{x:.0f}" y="{y - 13:.0f}" text-anchor="middle">{html.escape(n)}</text></g>')
        else:
            label = "GND" if n == "0" else n
            out.append(f'<g class="gnet"><circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="#fff" stroke="#77776d"/>'
                       f'<text x="{x + 7:.0f}" y="{y + 4:.0f}">{html.escape(label)}</text></g>')
    out.append("</svg>")
    return "".join(out)


def changed(edit):
    """Only the lines an edit actually changed: (removed, added)."""
    old, new = edit["old"].splitlines(), edit["new"].splitlines()
    return [ln for ln in old if ln not in new], [ln for ln in new if ln not in old]


def render() -> str:
    parts = parse_netlist()
    blocks = list(dict.fromkeys(p["block"] for p in parts))
    bugs = load_tasks(BOARD_FILE)
    logs = json.loads((ROOT / "evidence" / "board-agent-logs.json").read_text(encoding="utf-8"))
    data = {}
    for b in bugs:
        lg = logs[b["id"]]
        edited = sorted({ln.split()[0] for s in lg["repaired"]["steps"] if s.get("edit")
                         for side in changed(s["edit"]) for ln in side if ln.strip() and not ln.startswith("*")})
        data[b["id"]] = {"title": b["title"], "report": b["report"],
                         "parts": edited or [e["find"].split()[0] for e in b["edits"]],
                         "steps": [{"tool": s["tool"], "input": s["input"], "output": s["output"][:170],
                                    "diff": changed(s["edit"]) if s.get("edit") else None} for s in lg["repaired"]["steps"]],
                         "repaired": {k: lg["repaired"][k] for k in ("passed", "turns", "tokens", "trace_id")},
                         "original": lg["original"], "caveat": CAVEATS.get(b["id"], "")}
    chips = "".join(f'<span class="chip"><i style="background:{COLORS[i % len(COLORS)]}"></i>{html.escape(bl)}</span>'
                    for i, bl in enumerate(blocks))
    rows = "".join(f'<tr data-part="{html.escape(p["name"])}"><td><i class="dot" style="background:{COLORS[blocks.index(p["block"]) % len(COLORS)]}"></i>'
                   f'{html.escape(p["name"])}</td><td>{html.escape(p["block"])}</td><td>{html.escape(" – ".join(p["nets"]))}</td>'
                   f'<td>{html.escape(p["value"])}</td><td class="note">{html.escape(p["note"])}</td></tr>' for p in parts)
    buglist = "".join(f'<button class="bug" data-bug="{b["id"]}"><b>{b["id"]}</b> {html.escape(b["title"])}'
                      f'<span class="tag{" warn" if not data[b["id"]]["original"]["passed"] else ""}">original: '
                      f'{"fixed" if data[b["id"]]["original"]["passed"] else "refused"}</span></button>' for b in bugs)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Circuit explorer</title>
<meta name="description" content="Explore the sensor circuit at schematic level, its bring-up bugs, and how Mend's repaired worker fixed each one.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Instrument+Serif:ital@0;1&family=Pinyon+Script&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}
{ART_CSS}
body{{background:#e6e6dd}} .app{{display:grid;grid-template-columns:360px 1fr;min-height:100vh}}
aside{{background:#efefe7;border-right:1px solid var(--line);padding:18px;display:flex;flex-direction:column;gap:14px;max-height:100vh;position:sticky;top:0;overflow:auto}}
.brand{{font:800 20px 'Inter Tight',sans-serif;letter-spacing:-.02em;text-decoration:none}} .brand span{{font:500 12px Inter;color:var(--mute);margin-left:6px}}
.boardsel{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px 12px;display:flex;gap:10px;align-items:center}}
.boardsel i{{width:30px;height:30px;border-radius:8px;background:#2f6b3f;display:inline-block}} .side-h{{font:600 12px Inter;color:var(--mute);text-transform:uppercase;letter-spacing:.06em;margin:6px 0 0}}
.bug{{all:unset;cursor:pointer;display:block;box-sizing:border-box;width:100%;padding:8px 10px;border-radius:10px;font-size:14px}} .bug:hover,.bug.on{{background:#fff}}
.tag{{display:block;font-size:12px;color:var(--mute)}} .tag.warn{{color:var(--bad)}}
.log{{display:flex;flex-direction:column;gap:8px;font-size:13px}} .msg{{background:#fff;border-radius:12px;padding:10px 12px}}
.msg.user{{background:var(--ink);color:#fff}} .msg .who{{font:600 11px Inter;color:var(--mute);display:block;margin-bottom:3px}} .msg.user .who{{color:#bbb}}
.lstep{{border-left:2px solid var(--line);padding:2px 0 2px 10px;color:var(--mute)}} .lstep b{{color:var(--ink);font:600 12px 'JetBrains Mono',monospace}}
.lstep .out{{display:block;font:11.5px/1.45 'JetBrains Mono',monospace;color:#77776d;overflow-wrap:anywhere}}
.diff{{font:12px/1.5 'JetBrains Mono',monospace;background:#fff;border-radius:8px;padding:6px 8px;margin-top:4px}} .diff .rm{{color:var(--bad)}} .diff .add{{color:var(--ok)}}
.caveat{{background:#fff4e5;border:1px solid #e8c48a;border-radius:12px;padding:10px 12px}}
main{{padding:30px 34px}} .top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}}
main h1{{font:400 44px/1 'Instrument Serif',serif;margin:0}} main .lead{{color:var(--mute);margin:6px 0 0}}
.toggle{{display:inline-flex;background:#efefe7;border:1px solid var(--line);border-radius:12px;padding:3px}} .toggle button{{all:unset;cursor:pointer;padding:8px 16px;border-radius:9px;font-weight:500}}
.toggle button.on{{background:#fff;box-shadow:0 1px 2px #0001}} .chips{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}}
.chip{{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:14px;background:#f4f4ee}} .chip i,.dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
.canvas{{background:#f4f4ee;border:1px solid var(--line);border-radius:18px;padding:18px;min-height:520px}} .view{{display:none}} .view.on{{display:block}}
.graph{{width:100%;height:auto}} .graph text{{font:600 10.5px Inter;fill:#45453f}} .gnet text{{font:10px 'JetBrains Mono';fill:#8a8a80}}
.gnode.on circle{{stroke:var(--ink);stroke-width:4}} .canvas table{{font-size:13px}} tr.on td{{background:#fff4e5}} td.note{{color:var(--mute)}}
@media (max-width:900px){{.app{{grid-template-columns:1fr}} aside{{position:static;max-height:none}}}}
</style></head><body><div class="app">
<aside>
  <a class="brand" href="index.html">Mend<span>circuit explorer</span></a>
  <div class="boardsel"><i></i><div><b>Sensor circuit</b><br><span class="sub">basic board · board.cir · {len(parts)} parts · {len(bugs)} bugs</span></div></div>
  <p class="side-h">Bring-up bugs</p><div>{buglist}</div>
  <p class="side-h">Agent log · repaired worker</p><div class="log" id="log"><div class="msg"><span class="who">Mend</span>Pick a bug above to see how the repaired worker fixed it, step by step, read back from its neatlogs trace.</div></div>
  <p class="sub" style="font-size:12px">Back to <a class="link" href="hardware.html">Beyond software</a> · <a class="link" href="{REPO}">code</a></p>
</aside>
<main>
  <div class="top"><div><h1>Explorer</h1><p class="lead">The sensor circuit on a basic board, and how it connects. The parts a bug touched light up.</p></div>
  <div class="toggle" role="tablist"><button class="on" data-view="art">Circuit</button><button data-view="graph">Netlist</button><button data-view="table">Table</button></div></div>
  <div class="chips" id="chips" style="display:none">{chips}</div>
  <div class="canvas">
    <div class="view on" id="v-art">{art_svg()}<p class="sub" style="font-size:12px">A basic board: parts in schematic order, joined by copper traces generated from the
    netlist's nets. Blue is the 3.3 V rail, violet 5 V, orange the sensor signal. Illustrative, not a manufactured PCB layout. Hover a part.</p></div>
    <div class="view" id="v-graph">{graph_svg(parts, blocks)}<p class="sub" style="font-size:12px">Coloured dots are parts, small dots are nets (wires). This is what a schematic is: parts joined by nets.</p></div>
    <div class="view" id="v-table"><div class="tablewrap"><table><tr><th>Part</th><th>Block</th><th>Nets</th><th>Value</th><th>Note</th></tr>{rows}</table></div></div>
  </div>
</main></div>
<script>
var B={json.dumps(data, ensure_ascii=False)};
function esc(s){{var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}}
document.querySelectorAll('.toggle button').forEach(function(t){{t.onclick=function(){{
  document.querySelectorAll('.toggle button').forEach(function(x){{x.classList.toggle('on',x===t)}});
  document.querySelectorAll('.view').forEach(function(v){{v.classList.toggle('on',v.id==='v-'+t.dataset.view)}});
  document.getElementById('chips').style.display=t.dataset.view==='graph'?'flex':'none';}};}});
function pick(id){{var b=B[id],h='';
  document.querySelectorAll('.bug').forEach(function(x){{x.classList.toggle('on',x.dataset.bug===id)}});
  h+='<div class="msg user"><span class="who">Bug report · '+id+'</span>'+esc(b.report)+'</div>';
  b.steps.forEach(function(s){{h+='<div class="lstep"><b>'+esc(s.tool)+'</b> '+esc(s.input)+'<span class="out">'+esc(s.output)+'</span>';
    if(s.diff){{h+='<div class="diff">'+s.diff[0].map(function(l){{return '<div class="rm">− '+esc(l)+'</div>'}}).join('')+s.diff[1].map(function(l){{return '<div class="add">+ '+esc(l)+'</div>'}}).join('')+'</div>';}}
    h+='</div>';}});
  h+='<div class="msg"><span class="who">Result · repaired worker</span>'+(b.repaired.passed?'All checks pass':'Not fixed')+' in '+b.repaired.turns+' turns, '+b.repaired.tokens.toLocaleString()+' tokens. Trace '+esc(b.repaired.trace_id.slice(0,8))+'.</div>';
  if(b.caveat)h+='<div class="caveat"><b>Honest note.</b> '+esc(b.caveat)+'</div>';
  h+='<div class="msg"><span class="who">Original worker on the same bug</span>'+(b.original.passed?'Fixed it in '+b.original.turns+' turns, '+b.original.tokens.toLocaleString()+' tokens.':'Refused in '+b.original.turns+' turn: “'+esc(b.original.said)+'”')+'</div>';
  document.getElementById('log').innerHTML=h;
  var art=document.querySelector('.art');art.classList.add('dim');
  document.querySelectorAll('.art .apart').forEach(function(g){{var nl=(g.dataset.nl||'').split(' ');
    g.classList.toggle('lit',b.parts.indexOf(g.dataset.id)>=0||nl.some(function(n){{return b.parts.indexOf(n)>=0}}));}});
  document.querySelectorAll('.gnode').forEach(function(g){{g.classList.toggle('on',b.parts.indexOf(g.dataset.part)>=0)}});
  document.querySelectorAll('tr[data-part]').forEach(function(r){{r.classList.toggle('on',b.parts.indexOf(r.dataset.part)>=0)}});}}
document.querySelectorAll('.bug').forEach(function(x){{x.onclick=function(){{pick(x.dataset.bug)}}}});
pick('BD08');
</script></body></html>"""


if __name__ == "__main__":
    (ROOT / "circuit.html").write_text(render(), encoding="utf-8")
    print("wrote circuit.html")
