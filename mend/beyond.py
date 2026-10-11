"""Build hardware.html: Mend's repairs on two domains it never saw, digital chip designs and circuit schematics.

    python -m mend.beyond     (also run by `python -m mend.site`)

Every number comes from the run files (via mend.site.facts); waveforms come from evidence/waveforms.json
(scripts/hw_waveforms.py), schematic drawings from docs/img/schematics (scripts/draw_schematics.py), and
the Verilog sample from hardware/verilog (scripts/hw_demo.py). Building the page needs none of those tools.
"""

import json

from mend.report import REPO
from mend.site import CSS, esc, facts, repeat_card, tokens
from mend.tasks import BOARD_FILE, HARDWARE_FILE, ROOT, SCHEMATICS_FILE, load_tasks

CYCLE, ROW, LEFT = 34, 34, 92  # timing diagram geometry, px


def timing_svg(rows_ok: list[dict], rows_bug: list[dict]) -> str:
    """Correct and buggy waveforms, one under the other; cycles where they differ are shaded and marked."""
    signals = list(rows_ok[0])
    n = len(rows_ok)
    lanes = [(f"{s}", rows_ok, s) for s in signals] + [(f"{s} (bug)", rows_bug, s) for s in signals]
    width, height = LEFT + n * CYCLE + 10, len(lanes) * ROW + 30
    parts = [f'<svg class="wave" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="timing diagram">']
    for c in range(n):
        if rows_ok[c] != rows_bug[c]:
            x = LEFT + c * CYCLE
            parts.append(f'<rect x="{x}" y="0" width="{CYCLE}" height="{height - 22}" fill="var(--bad)" opacity=".13"/>'
                         f'<text x="{x + CYCLE / 2}" y="{height - 6}" text-anchor="middle" class="mark">▲</text>')
    for c in range(n + 1):
        parts.append(f'<line x1="{LEFT + c * CYCLE}" y1="0" x2="{LEFT + c * CYCLE}" y2="{height - 22}" stroke="var(--line)"/>')
    for i, (label, rows, sig) in enumerate(lanes):
        top = i * ROW + 6
        parts.append(f'<text x="0" y="{top + 18}" class="lane">{esc(label)}</text>')
        values = [r[sig] for r in rows]
        if max(r[sig] for r in rows_ok + rows_bug) <= 1:  # one bit: a step line
            pts = []
            for c, v in enumerate(values):
                y = top + (4 if v else 24)
                pts += [(LEFT + c * CYCLE, y), (LEFT + (c + 1) * CYCLE, y)]
            parts.append('<polyline fill="none" stroke="var(--ink)" stroke-width="2" points="'
                         + " ".join(f"{x},{y}" for x, y in pts) + '"/>')
        else:  # a bus: value in each cycle
            for c, v in enumerate(values):
                x = LEFT + c * CYCLE
                parts.append(f'<rect x="{x + 2}" y="{top + 2}" width="{CYCLE - 4}" height="22" rx="5" fill="none" stroke="var(--ink)"/>'
                             f'<text x="{x + CYCLE / 2}" y="{top + 18}" text-anchor="middle" class="bus">{v}</text>')
    parts.append("</svg>")
    return "".join(parts)


def result_block(before: list, after: list, total_label: str) -> str:
    if not (before and after):
        return '<p class="sub">Runs not recorded yet.</p>'
    pb, pa = (sum(r["passed"] for r in g) / len(g) for g in (before, after))
    tb, ta = (sum(tokens(r) for r in g) / len(g) for g in (before, after))
    solved = lambda g: ", ".join(str(r["passed"]) for r in g)  # noqa: E731
    head = (f"{solved(before)} → {solved(after)} {total_label} solved." if pa > pb else
            f"Same {pa:g}/{before[0]['total']}, at {(1 - ta / tb) * 100:.0f}% fewer tokens." if ta < tb * 0.85 else
            "No clear gain carried over.")
    return (f'<h3 class="verdict">{esc(head)}</h3><div class="ba two-col">'
            f'{repeat_card("Original worker", before, None, "")}{repeat_card("After self-repair", after, None, "")}</div>')  # both pass: no red


def bug_table(path) -> str:
    rows = "".join(f"<tr><td>{esc(t['id'])}</td><td>{esc(t['title'])}</td><td class='rep'>{esc(t['report'])}</td></tr>"
                   for t in load_tasks(path))
    return f'<div class="tablewrap"><table><tr><th>Bug</th><th>What it is</th><th>Bug report the agent got</th></tr>{rows}</table></div>'


def render() -> str:
    f = facts()
    waves = json.loads((ROOT / "evidence" / "waveforms.json").read_text(encoding="utf-8"))
    wave_cards = "".join(
        f'<div class="card"><span class="k">{esc(w["caption"])}</span>'
        f'<span class="sub">Planted bug {esc(w["task"])}: {esc(w["report"])}</span>'
        f'{timing_svg(w["correct"], w["buggy"])}<span class="sub">▲ marks the cycles where the bug shows.</span></div>'
        for w in waves.values())
    verilog = (ROOT / "hardware" / "verilog" / "pwm.v").read_text(encoding="utf-8")
    drawings = [("divider", "Voltage divider: 5 V to 3.3 V"), ("led", "LED driver: 10 mA"), ("lowpass", "RC low-pass, 1 kHz"),
                ("highpass", "RC high-pass, 1 kHz"), ("noninv", "Non-inverting amplifier, gain 11"),
                ("inverting", "Inverting amplifier, gain -4.7"), ("pullup", "Button with pull-up")]
    sch = "".join(f'<figure class="card"><img src="docs/img/schematics/{n}.svg" alt="{esc(c)} schematic" loading="lazy">'
                  f'<figcaption class="k">{esc(c)}</figcaption></figure>' for n, c in drawings)
    netlist = (ROOT / "schematics" / "circuits" / "divider.cir").read_text(encoding="utf-8")
    hw_n = len(load_tasks(HARDWARE_FILE))
    sc_n = len(load_tasks(SCHEMATICS_FILE))
    bd_n = len(load_tasks(BOARD_FILE))
    checks = [line.split("def ")[1].split("(")[0] for line in
              (ROOT / "schematics" / "tests" / "test_board.py").read_text(encoding="utf-8").splitlines() if line.startswith("def test_")]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mend on hardware</title>
<meta name="description" content="Mend's self-repairs, tested on chip designs and circuit schematics it never saw.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600;800&family=Instrument+Serif:ital@0;1&family=Pinyon+Script&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
{CSS}
.wave{{max-width:100%;height:auto;margin:10px 0;font:12px 'JetBrains Mono',monospace}} .wave .lane{{fill:var(--mute)}}
.wave .bus{{fill:var(--ink)}} .wave .mark{{fill:var(--bad);font-size:11px}}
.waves{{display:grid;gap:18px;margin-top:28px}} .waves .card{{overflow-x:auto}}
.sch{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-top:28px}}
.sch figure{{margin:0}} .sch img{{width:100%;height:190px;object-fit:contain;background:#fff;border-radius:14px}}
pre.code{{font:12.5px/1.55 'JetBrains Mono',monospace;background:#fff;border-radius:16px;padding:18px;overflow:auto;max-height:420px;margin:0}}
.verdict{{font:800 clamp(26px,3.4vw,40px)/1.05 'Inter Tight',sans-serif;letter-spacing:-.03em;margin:28px 0 0}}
td.rep{{color:var(--mute)}} .hero2{{font:800 clamp(56px,10vw,128px)/.88 'Inter Tight',sans-serif;letter-spacing:-.05em;margin:0}}
</style></head><body>
<nav><div class="wrap"><a class="logo" href="index.html"><b>Mend</b><span>neatHack 2026</span></a>
<div class="links"><a class="hide" href="#chips">Chip designs</a><a class="hide" href="#schematics">Schematics</a><a class="hide" href="#board">Sensor circuit</a>
<a class="hide" href="index.html">Main page</a><a class="pill" href="{REPO}">View the code</a></div></div></nav>

<header><div class="wrap">
  <p class="eyebrow">Beyond software</p>
  <h1 class="hero2">Same repairs.<br>New domains.</h1>
  <p class="lede"><span class="cap">M</span>end repaired itself on Python bugs. Then we gave both workers bugs in chip designs and
  circuit schematics they had never seen.</p>
  <p class="intro">Nothing here was shown to the supervisor or used in a self-repair round. The "hardware" is checked in simulation,
  as chip and board designers check designs before manufacturing.</p>
</div></header>

<section id="chips"><div class="wrap">
  <p class="eyebrow">Digital chip designs · Amaranth HDL → Verilog</p><h2>{hw_n} bugs in 8 designs.</h2>
  <p class="sub">A counter, Gray-code converters, an 8-bit ALU, a FIFO, a UART transmitter, a PWM generator, a debouncer and a CRC-8 unit,
  written in <a class="link" href="https://amaranth-lang.org">Amaranth HDL</a> and checked cycle by cycle by 26 simulation testbenches.</p>
  {result_block(f["hw_before"], f["hw_after"], f"of {hw_n}")}
  <div class="waves">{wave_cards}</div>
  <div class="two" style="margin-top:36px;align-items:start">
    <div><p class="eyebrow">Real hardware output</p><p>Every design exports as Verilog, the language chip toolchains take.
    This is the PWM generator, emitted by Amaranth through Yosys
    (<a class="link" href="{REPO}/tree/main/hardware/verilog">hardware/verilog</a>).</p></div>
    <pre class="code">{esc(verilog)}</pre>
  </div>
  <p class="eyebrow" style="margin-top:36px">The planted bugs</p>{bug_table(HARDWARE_FILE)}
</div></section>

<section id="schematics"><div class="wrap">
  <p class="eyebrow">Circuit schematics · netlists checked by circuit simulation</p><h2>{sc_n} bugs in 7 circuits.</h2>
  <p class="sub">A netlist is the text form of a schematic, the file KiCad exports and SPICE simulates. A small simulator (Modified Nodal Analysis,
  checked against hand calculations) tests each circuit against its spec.</p>
  {result_block(f["sc_before"], f["sc_after"], f"of {sc_n}")}
  <div class="sch">{sch}</div>
  <div class="two" style="margin-top:36px;align-items:start">
    <div><p class="eyebrow">What the agent edits</p><p>The divider above, as the netlist the agent reads and fixes. A planted bug changes one
    line, for example R2 20k becoming 2k, and the agent gets only the symptom: "the 3.3 V reference measures about 0.83 V".</p></div>
    <pre class="code">{esc(netlist)}</pre>
  </div>
  <p class="eyebrow" style="margin-top:36px">The planted bugs</p>{bug_table(SCHEMATICS_FILE)}
</div></section>

<section id="board"><div class="wrap">
  <p class="eyebrow">A larger schematic · one netlist, shared power rails</p><h2>A sensor circuit, brought up in simulation.</h2>
  <p class="sub">USB 5 V in, an LM317-style regulator set to 3.3 V, an NTC temperature sensor with an op-amp buffer and a 1 kHz anti-aliasing
  filter into the microcontroller's ADC, a reset circuit, power and status LEDs, and I²C pull-ups. {len(checks)} bring-up checks, the ones an
  engineer runs on a new board: is the rail 3.3 V, are the LEDs safe, does the sensor read right, is anything over the MCU's 3.6 V limit.</p>
  <p><a class="pill" href="circuit.html">Open the circuit explorer: the circuit illustrated, every bug, the agent's steps →</a></p>
  <p class="sub" style="font-size:13px">The circuit: <a class="link" href="{REPO}/blob/main/schematics/circuits/board.cir">board.cir</a>,
  checked by <a class="link" href="{REPO}/blob/main/schematics/tests/test_board.py">test_board.py</a>. Schematic level only: no PCB layout.</p>
  {result_block(f["bd_before"], f["bd_after"], f"of {bd_n}")}
  <p class="sub" style="font-size:15px">Where the gap comes from: the original worker <b>refused</b> BD01 (both runs) and BD02 (one run) in a
  single turn, replying that a sensor-board report is "a hardware issue, not a bug in the Python library", without running a check. Both workers
  get the same prompt. The repaired worker's learned workflow starts by running the tests, so it engaged and fixed all 8.</p>
  <p class="eyebrow" style="margin-top:36px">The planted bring-up bugs</p>{bug_table(BOARD_FILE)}
</div></section>

<section id="honest"><div class="wrap">
  <p class="eyebrow">What this shows, and what it doesn't</p><h2>The gain is efficiency.</h2>
  <p class="sub">Both workers fix every chip-design and schematic bug, so these sets show no gain in what gets solved. What carried over is how:
  the self-repaired worker reads less, edits precisely and stops when the tests pass, so it needs far fewer turns and tokens.
  Two runs per worker; the sets are small; everything is simulated, not built on a physical board.</p>
  <div class="cta"><a class="pill" href="{REPO}/tree/main/hardware">Hardware designs</a><a class="pill ghost" href="{REPO}/tree/main/schematics">Circuits and simulator</a>
  <a class="pill ghost" href="index.html">Back to the main page</a></div>
</div></section>

<footer><div class="wrap">Try it yourself: <code>python -m pytest -q hardware schematics</code>, then
<code>python scripts/hw_demo.py bugs</code>. · <a href="{REPO}">github.com/thegoodengineers/mend</a></div></footer>
</body></html>"""


if __name__ == "__main__":
    (ROOT / "hardware.html").write_text(render(), encoding="utf-8")
    print("wrote hardware.html")
