"""An isometric drawing of the sensor board (schematics/circuits/board.cir) for hardware.html.

Plain SVG, painted back to front, with one small script: hovering or tapping a part shows what it does,
the bring-up check that covers it (schematics/tests/test_board.py) and the bug planted in it
(tasks/board.json). The layout is illustrative; the circuit itself is the netlist.
"""

import html
import json
import math

S = 17                      # px per board unit
COS, SIN = math.cos(math.pi / 6), math.sin(math.pi / 6)
BOARD = (30, 20, 0.8)       # width, depth, thickness in board units
OX, OY = 330, 60            # screen offset of the board's back corner

# (id, label, x, y, w, d, h, top colour, side colour, role, check, bugs)
PARTS = [
    ("J1", "USB", 0.2, 8, 3.2, 4, 2.2, "#c9ccd1", "#9ea3aa", "USB connector: 5 V in", "", ""),
    ("C1", "CIN", 4.5, 13.5, 1.6, 1.6, 2.4, "#3f6fb5", "#2c5089", "10 µF input bulk capacitor", "", ""),
    ("U1", "LM317", 4.5, 5, 3, 2.4, 1.6, "#2a2a2a", "#151515",
     "Adjustable regulator: 5 V to 3.3 V, set by RSET and RADJ", "test_rail_is_3v3", "BD01"),
    ("R1", "RSET/RADJ", 8.6, 3.2, 2.2, 1, 0.6, "#d8c9a3", "#b5a47c",
     "Regulator feedback resistors: 1.25 V × (1 + 392/240) = 3.3 V", "test_rail_is_3v3", "BD01"),
    ("C2", "COUT", 8.4, 7.4, 1.6, 1.6, 2.4, "#3f6fb5", "#2c5089", "10 µF output capacitor", "", ""),
    ("D1", "PWR", 4.6, 1.2, 1.2, 1.2, 1, "#4cc76a", "#2f8a45",
     "Green power-on LED through 1k: about 1.2 mA", "test_power_led_on_at_about_1ma", "BD02"),
    ("TH1", "NTC", 12.5, 15.2, 1.2, 1.2, 1.4, "#3a3a3a", "#222",
     "NTC thermistor, 10k at 25 °C, over a 10k fixed resistor: 1.65 V at 25 °C",
     "test_sensor_reads_half_rail_at_25c", "BD03"),
    ("U3", "OPAMP", 14.8, 11.6, 2.4, 2, 1, "#2a2a2a", "#151515",
     "Op-amp voltage follower: the ADC does not load the sensor divider",
     "test_adc_sees_the_buffered_sensor_voltage", "BD04"),
    ("F1", "RC 1kHz", 18, 12, 2.2, 1.2, 0.8, "#d8c9a3", "#b5a47c",
     "Anti-aliasing RC filter, 1.59k + 100 nF: cutoff 1 kHz", "test_anti_aliasing_cutoff_is_1khz", "BD05"),
    ("U2", "MCU", 19, 4, 6.5, 6.5, 1.1, "#262626", "#111",
     "Microcontroller: ADC, RESET, GPIO and I²C pins (represented by its pins in the netlist)", "", ""),
    ("SW1", "RESET", 26.5, 13.5, 2.4, 2.4, 1.4, "#cfcfcf", "#a3a3a3",
     "Reset button with a 10k pull-up and 100 nF debounce", "test_board_runs_when_reset_released", "BD06"),
    ("D2", "STATUS", 27, 8.6, 1.2, 1.2, 1, "#e0524d", "#a8332f",
     "Red status LED on a GPIO pin through 220 Ω: about 6 mA (pin limit 20 mA)",
     "test_status_led_current_is_safe_for_the_gpio", "BD07"),
    ("J2", "I²C", 26.5, 1, 3, 1.2, 2.2, "#262626", "#111",
     "I²C header with 4.7k pull-ups to 3.3 V (MCU pins: 3.6 V max)",
     "test_i2c_lines_idle_high_within_mcu_limits", "BD08"),
]


def iso(x, y, z=0.0):
    return OX + (x - y) * COS * S, OY + (x + y) * SIN * S - z * S


def poly(points, fill, extra=""):
    return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in points)}" fill="{fill}" {extra}/>'


def box(x, y, z, w, d, h, top, side):
    """Top, left (front-left) and right (front-right) faces of a box sitting at height z."""
    t = [iso(x, y, z + h), iso(x + w, y, z + h), iso(x + w, y + d, z + h), iso(x, y + d, z + h)]
    left = [iso(x, y + d, z + h), iso(x + w, y + d, z + h), iso(x + w, y + d, z), iso(x, y + d, z)]
    right = [iso(x + w, y, z + h), iso(x + w, y + d, z + h), iso(x + w, y + d, z), iso(x + w, y, z)]
    return poly(left, side) + poly(right, side, 'opacity=".78"') + poly(t, top, 'stroke="#0005" stroke-width=".6"')


def board_svg() -> str:
    bw, bd, bt = BOARD
    parts = [box(0, 0, 0, bw, bd, bt, "#2f6b3f", "#1f4a2b")]
    for gx in range(2, int(bw), 3):  # copper traces, for texture
        parts.append(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in (iso(gx, 0.6, bt), iso(gx, bd - 0.6, bt)))}" '
                     f'stroke="#c9a54a" stroke-opacity=".28" stroke-width="1"/>')
    mx, my, mw, md = 19, 4, 6.5, 6.5  # MCU pins: small silver legs along all four sides, under the body
    for i in range(8):
        t = 0.6 + i * 0.75
        for px, py, pw, pd in ((mx + t, my - 0.5, 0.3, 0.6), (mx + t, my + md - 0.1, 0.3, 0.6),
                               (mx - 0.5, my + t, 0.6, 0.3), (mx + mw - 0.1, my + t, 0.6, 0.3)):
            parts.append(box(px, py, bt, pw, pd, 0.25, "#d9dadc", "#a9abaf"))
    for p in sorted(PARTS, key=lambda p: p[2] + p[4] + p[3] + p[5]):  # back to front
        pid, label, x, y, w, d, h, top, side, role, check, bug = p
        lx, ly = iso(x + w / 2, y + d / 2, bt + h)
        parts.append(f'<g class="part" tabindex="0" data-id="{pid}">{box(x, y, bt, w, d, h, top, side)}'
                     f'<text x="{lx:.1f}" y="{ly - 6:.1f}" text-anchor="middle" class="plabel">{html.escape(label)}</text></g>')
    width, height = iso(bw, 0)[0] + 40, iso(bw, bd)[1] + 40
    return (f'<svg class="iso" viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
            f'aria-label="Isometric drawing of the sensor board">{"".join(parts)}</svg>')


def board_block() -> str:
    info = {p[0]: {"name": f"{p[0]} · {p[1]}", "role": p[9], "check": p[10], "bug": p[11]} for p in PARTS}
    return f"""<div class="isowrap card"><div class="isofig">{board_svg()}</div>
<div class="isoinfo" id="isoinfo" aria-live="polite"><span class="k">Hover or tap a part</span>
<span class="sub">Each part shows what it does, the bring-up check that covers it, and the bug planted in it.</span></div></div>
<script>(function(){{var I={json.dumps(info)},box=document.getElementById('isoinfo');
function show(id){{var p=I[id];box.innerHTML='<span class="k">'+p.name+'</span><span class="sub">'+p.role+'</span>'
+(p.check?'<span class="sub">Check: <code>'+p.check+'</code></span>':'')+(p.bug?'<span class="sub">Planted bug: <b>'+p.bug+'</b></span>':'');}}
document.querySelectorAll('.iso .part').forEach(function(g){{['mouseenter','focus','click'].forEach(function(e){{
g.addEventListener(e,function(){{document.querySelectorAll('.iso .part.on').forEach(function(o){{o.classList.remove('on')}});g.classList.add('on');show(g.dataset.id);}});}});}});}})();</script>"""


CSS = """.isowrap{display:grid;grid-template-columns:1.6fr 1fr;gap:20px;align-items:center;margin-top:28px}
.iso{width:100%;height:auto} .iso .part{cursor:pointer;outline:none} .iso .part:hover polygon,.iso .part.on polygon{filter:brightness(1.35)}
.iso .plabel{font:600 10.5px Inter,sans-serif;fill:#fff;paint-order:stroke;stroke:#0009;stroke-width:2.5px;pointer-events:none}
.isoinfo{display:flex;flex-direction:column;gap:8px} @media (max-width:820px){.isowrap{grid-template-columns:1fr}}"""
