"""An isometric technical illustration of the sensor circuit (schematics/circuits/board.cir), for circuit.html.

Light line art with four-tone shading on a ruled base plate; parts are laid out in schematic order (power,
sensor chain, microcontroller, outputs) and wired as the netlist connects them. Not a PCB layout. The rails
and the sensor signal glow and flow; LEDs light. Plain SVG and CSS, written here (no third-party code).
"""

import html
import math

S = 16                                  # px per unit
C30, S30 = math.cos(math.pi / 6), math.sin(math.pi / 6)
PLATE = (39.5, 24.5, 1.2)               # width, depth, height (units)
OX, OY = 420, 40
INK = "#5f5f58"

# art id -> (label, netlist parts it is, role, check, bug)
INFO = {
    "J1": ("USB connector", ["VUSB", "CIN"], "5 V in from USB, with a 10 µF input capacitor", "", ""),
    "U1": ("LM317 regulator", ["VREF", "EREG"], "Adjustable regulator: 5 V to 3.3 V, set by RSET and RADJ", "test_rail_is_3v3", "BD01"),
    "RSET": ("RSET 240 Ω", ["RSET"], "Regulator feedback, top", "test_rail_is_3v3", "BD01"),
    "RADJ": ("RADJ 392 Ω", ["RADJ"], "Regulator feedback, bottom: 1.25 V × (1 + 392/240) = 3.3 V", "test_rail_is_3v3", "BD01"),
    "COUT": ("COUT 10 µF", ["COUT"], "Regulator output capacitor", "", ""),
    "RPWR": ("RPWR 1k", ["RPWR"], "Power-LED resistor", "test_power_led_on_at_about_1ma", "BD02"),
    "DPWR": ("Power LED", ["DPWR"], "Green power-on LED: about 1.2 mA", "test_power_led_on_at_about_1ma", "BD02"),
    "RNTC": ("NTC thermistor", ["RNTC"], "10k at 25 °C; its resistance falls as it warms", "test_sensor_voltage_rises_when_warm", "BD03"),
    "RFIX": ("RFIX 10k", ["RFIX"], "Fixed half of the sensor divider: 1.65 V at 25 °C", "test_sensor_reads_half_rail_at_25c", "BD03"),
    "TP1": ("TP1 test point", ["VTP1"], "Where a 1 V AC test signal is injected to check the filter", "", ""),
    "U3": ("Op-amp buffer", ["EBUF"], "Voltage follower, so the ADC does not load the divider", "test_adc_sees_the_buffered_sensor_voltage", "BD04"),
    "RAA": ("RAA 1.59k", ["RAA"], "Anti-aliasing filter resistor", "test_anti_aliasing_cutoff_is_1khz", "BD05"),
    "CAA": ("CAA 100 nF", ["CAA"], "Anti-aliasing filter capacitor: cutoff 1 kHz", "test_anti_aliasing_cutoff_is_1khz", "BD05"),
    "U2": ("Microcontroller", ["VGPIO"], "Reads the ADC, drives the status LED, talks I²C (represented by its pins)", "", ""),
    "RRST": ("RRST 10k", ["RRST"], "Reset pull-up: keeps the MCU running", "test_board_runs_when_reset_released", "BD06"),
    "CRST": ("CRST 100 nF", ["CRST"], "Reset debounce capacitor", "", ""),
    "SW1": ("Reset button", ["RBTN"], "Pulls RESET low when pressed", "test_reset_button_pulls_reset_low", ""),
    "RLED": ("RLED 220 Ω", ["RLED"], "Status-LED resistor: about 6 mA (GPIO limit 20 mA)", "test_status_led_current_is_safe_for_the_gpio", "BD07"),
    "DLED": ("Status LED", ["DLED"], "Red status LED on a GPIO pin", "test_status_led_current_is_safe_for_the_gpio", "BD07"),
    "RSDA": ("RSDA 4.7k", ["RSDA"], "I²C data pull-up to 3.3 V (MCU pins: 3.6 V max)", "test_i2c_lines_idle_high_within_mcu_limits", "BD08"),
    "RSCL": ("RSCL 4.7k", ["RSCL"], "I²C clock pull-up to 3.3 V", "test_i2c_lines_idle_high_within_mcu_limits", "BD08"),
    "J2": ("I²C header", [], "SDA, SCL, 3.3 V and GND out to a sensor bus", "test_i2c_lines_idle_high_within_mcu_limits", "BD08"),
}

# Pin positions (plate units) of every part, and the nets that join them (as in board.cir, plus the USB-to-regulator
# input a real board has; the simulation models the regulator by its output). "0" is ground: drawn as ground marks.
PINS = {
    "J1.5V": (3.7, 4.6), "J1.GND": (2.0, 6.0), "CIN.+": (5.2, 4.0), "CIN.-": (5.2, 5.4),
    "U1.ADJ": (8.11, 5.1), "U1.OUT": (8.96, 5.1), "U1.IN": (9.81, 5.1),
    "RSET.a": (11.5, 3.35), "RSET.b": (14.2, 3.35), "RADJ.a": (15.1, 5.35), "RADJ.b": (17.8, 5.35),
    "COUT.+": (19.6, 3.9), "COUT.-": (19.6, 5.3), "RPWR.a": (21.0, 3.35), "RPWR.b": (23.7, 3.35),
    "DPWR.A": (24.7, 3.35), "DPWR.K": (25.9, 3.35),
    "RNTC.a": (4.3, 12.0), "RNTC.b": (5.7, 12.0), "RFIX.a": (6.9, 12.0), "RFIX.b": (9.6, 12.0), "RFIX.gnd": (9.6, 12.0),
    "TP1": (11.0, 12.0), "U3.IN+": (13.05, 10.6), "U3.IN-": (13.5, 10.6), "U3.OUT": (14.4, 13.4), "U3.V-": (13.05, 13.4),
    "RAA.a": (15.9, 12.0), "RAA.b": (18.6, 12.0), "CAA.a": (19.6, 12.0), "CAA.b": (20.6, 12.0),
    "U2.ADC": (23.6, 11.8), "U2.VDD": (26.0, 8.6), "U2.GND": (27.6, 8.6), "U2.RST": (24.4, 15.0), "U2.GPIO": (26.0, 15.0),
    "U2.SDA": (30.0, 10.2), "U2.SCL": (30.0, 11.0),
    "RRST.a": (3.5, 18.55), "RRST.b": (6.2, 18.55), "CRST.a": (7.4, 18.55), "CRST.b": (8.4, 18.55),
    "SW1.a": (10.0, 18.6), "SW1.b": (12.0, 18.6), "RLED.a": (16.3, 19.55), "RLED.b": (19.0, 19.55),
    "DLED.A": (20.0, 19.55), "DLED.K": (21.2, 19.55),
    "RSDA.a": (31.9, 17.55), "RSDA.b": (34.6, 17.55), "RSCL.a": (31.9, 19.95), "RSCL.b": (34.6, 19.95),
    "J2.GND": (35.1, 22.0), "J2.3V3": (35.95, 22.0), "J2.SDA": (36.8, 22.0), "J2.SCL": (37.65, 22.0),
}
NETS = {  # net -> pins; class by net: usb (5 V), v33 (3.3 V), sig (the sensor signal path), io (everything else)
    "usb": ["J1.5V", "CIN.+", "U1.IN"],
    "v33": ["U1.OUT", "RSET.a", "COUT.+", "RPWR.a", "RNTC.a", "RRST.a", "U2.VDD", "RSDA.a", "RSCL.a", "J2.3V3"],
    "adj": ["U1.ADJ", "RSET.b", "RADJ.a"], "pled": ["RPWR.b", "DPWR.A"],
    "sense": ["RNTC.b", "RFIX.a"], "ain": ["RFIX.a", "TP1", "U3.IN+"], "buf": ["U3.IN-", "U3.OUT", "RAA.a"],
    "adc": ["RAA.b", "CAA.a", "U2.ADC"], "rst": ["RRST.b", "CRST.a", "SW1.a", "U2.RST"], "gpio": ["U2.GPIO", "RLED.a"],
    "sled": ["RLED.b", "DLED.A"], "sda": ["RSDA.b", "U2.SDA", "J2.SDA"], "scl": ["RSCL.b", "U2.SCL", "J2.SCL"],
    "0": ["J1.GND", "CIN.-", "RADJ.b", "COUT.-", "DPWR.K", "RFIX.b", "U3.V-", "CAA.b", "U2.GND", "CRST.b", "SW1.b", "DLED.K", "J2.GND"],
}
TRUNK_V33 = 8.0  # the 3.3 V rail runs along this line; every 3.3 V pin drops onto it
NET_CLASS = {"usb": "usb", "v33": "v33", "sense": "sig", "ain": "sig", "buf": "sig", "adc": "sig"}


def routes():
    """Wire polylines per net: the 3.3 V rail as a trunk with drops, other nets as L-shaped links in x order."""
    out = []
    for net, pins in NETS.items():
        if net == "0":
            continue
        xy = [PINS[p] for p in pins]
        cls = NET_CLASS.get(net, "io")
        if net == "v33":
            xs = [x for x, _ in xy]
            out.append((cls, [(min(xs), TRUNK_V33), (max(xs), TRUNK_V33)]))
            out += [(cls, [(x, y), (x, TRUNK_V33)]) for x, y in xy]
            continue
        xy.sort()
        for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
            out.append((cls, [(x1, y1), (x2, y1), (x2, y2)]))
    return out


def iso(x, y, z=0.0):
    return OX + (x - y) * C30 * S, OY + (x + y) * S30 * S - z * S


def pts(seq):
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in seq)


def box(x, y, z, w, d, h, top="#fbfbf8", left="#ebebe5", right="#dcdcd4", stroke=INK, sw=0.7):
    t = [iso(x, y, z + h), iso(x + w, y, z + h), iso(x + w, y + d, z + h), iso(x, y + d, z + h)]
    lf = [iso(x, y + d, z + h), iso(x + w, y + d, z + h), iso(x + w, y + d, z), iso(x, y + d, z)]
    rt = [iso(x + w, y, z + h), iso(x + w, y + d, z + h), iso(x + w, y + d, z), iso(x + w, y, z)]
    style = f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"'
    return (f'<polygon points="{pts(lf)}" fill="{left}" {style}/><polygon points="{pts(rt)}" fill="{right}" {style}/>'
            f'<polygon points="{pts(t)}" fill="{top}" {style}/>')


def cyl(cx, cy, z, r, h, top="#fbfbf8", side="#e3e3dc", stroke=INK, extra=""):
    """Upright cylinder: side band, then the top ellipse."""
    x, y0 = iso(cx, cy, z)
    _, y1 = iso(cx, cy, z + h)
    rx, ry = 1.2247 * r * S, 0.7071 * r * S
    side_path = (f'M{x - rx:.1f},{y1:.1f} L{x - rx:.1f},{y0:.1f} A{rx:.1f},{ry:.1f} 0 0 0 {x + rx:.1f},{y0:.1f} '
                 f'L{x + rx:.1f},{y1:.1f} Z')
    return (f'<path d="{side_path}" fill="{side}" stroke="{stroke}" stroke-width=".7"/>'
            f'<ellipse cx="{x:.1f}" cy="{y1:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{top}" stroke="{stroke}" stroke-width=".7" {extra}/>')


def resistor(x, y, z, bands):
    """Axial resistor lying along x, on two pads, with colour bands."""
    out = box(x - 0.3, y + 0.15, z, 0.4, 0.4, 0.06, "#e9dfc4", "#d6c9a6", "#c7b893")
    out += box(x + 2.3, y + 0.15, z, 0.4, 0.4, 0.06, "#e9dfc4", "#d6c9a6", "#c7b893")
    out += box(x, y, z + 0.25, 2.4, 0.7, 0.7, "#f3ead3", "#e6d9b8", "#d8c9a3")
    for i, c in enumerate(bands):
        out += box(x + 0.45 + i * 0.45, y - 0.02, z + 0.24, 0.18, 0.74, 0.74, c, c, c, stroke=INK, sw=0.4)
    return out


def chip(x, y, z, w, d, h, pins_x, pins_y, label=""):
    out = ""
    for i in range(pins_x):
        px = x + (i + 0.5) * w / pins_x - 0.1
        out += box(px, y - 0.45, z, 0.2, 0.5, 0.18, "#e9e9ec", "#cfd0d4", "#bfc0c5", sw=0.4)
        out += box(px, y + d - 0.05, z, 0.2, 0.5, 0.18, "#e9e9ec", "#cfd0d4", "#bfc0c5", sw=0.4)
    for i in range(pins_y):
        py = y + (i + 0.5) * d / pins_y - 0.1
        out += box(x - 0.45, py, z, 0.5, 0.2, 0.18, "#e9e9ec", "#cfd0d4", "#bfc0c5", sw=0.4)
        out += box(x + w - 0.05, py, z, 0.5, 0.2, 0.18, "#e9e9ec", "#cfd0d4", "#bfc0c5", sw=0.4)
    out += box(x, y, z + 0.1, w, d, h, "#4a4a46", "#3a3a37", "#2e2e2b", stroke="#222", sw=0.6)
    dx, dy = iso(x + 0.6, y + 0.6, z + 0.1 + h)
    out += f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="2" fill="#8a8a84"/>'
    if label:
        lx, ly = iso(x + w / 2, y + d / 2, z + 0.1 + h)
        out += f'<text x="{lx:.1f}" y="{ly + 3:.1f}" text-anchor="middle" class="chiptext">{html.escape(label)}</text>'
    return out


def led(cx, cy, z, color, glow):
    out = box(cx - 0.6, cy - 0.6, z, 1.2, 1.2, 0.25)
    out += cyl(cx, cy, z + 0.25, 0.48, 0.7, top=color, side=color, extra='opacity=".95"')
    gx, gy = iso(cx, cy, z + 1.1)
    out += f'<circle class="ledglow" cx="{gx:.1f}" cy="{gy:.1f}" r="16" fill="url(#{glow})"/>'
    return out


def parts_svg(z):
    """Each part as a hoverable group, painted back to front."""
    P = {}  # id -> (paint order, svg); positions match PINS
    P["J1"] = (4, box(0.4, 3.4, z, 3.2, 2.4, 1.6, "#eef0f3", "#d9dde2", "#c8cdd4") + box(0.2, 3.9, z + 0.4, 0.25, 1.4, 0.8, "#55575c", "#44464a", "#3a3c40")
               + cyl(5.2, 4.7, z, 0.5, 1.4))
    P["U1"] = (8, box(7.6, 2.2, z, 2.8, 0.4, 2.8, "#e7e9ec", "#cdd1d6", "#bdc2c8") + box(7.6, 2.6, z, 2.8, 1.4, 1.6, "#4a4a46", "#3a3a37", "#2e2e2b", stroke="#222")
               + "".join(box(8.0 + i * 0.85, 4.0, z, 0.22, 1.1, 0.22, "#e9e9ec", "#cfd0d4", "#bfc0c5", sw=0.4) for i in range(3)))
    P["RSET"] = (13, resistor(11.6, 3.0, z, ["#c24", "#d9b236", "#7a4a1e"]))
    P["RADJ"] = (18, resistor(15.2, 5.0, z, ["#e07a2e", "#c24", "#c24"]))
    P["COUT"] = (21, cyl(19.6, 4.6, z, 0.7, 2.0))
    P["RPWR"] = (22, resistor(21.1, 3.0, z, ["#7a4a1e", "#111", "#c24"]))
    P["DPWR"] = (27, led(25.3, 3.35, z, "#7fd38f", "glowGreen"))
    P["RNTC"] = (16, box(4.3, 11.9, z, 1.4, 0.2, 0.12, "#d9dadc", "#c3c4c7", "#b5b6b9", sw=0.4) + cyl(5.0, 12.0, z + 0.1, 0.42, 0.55, top="#5d5d57", side="#4b4b46"))
    P["RFIX"] = (19, resistor(7.0, 11.65, z, ["#7a4a1e", "#111", "#e07a2e"]))
    P["TP1"] = (23, cyl(11.0, 12.0, z, 0.25, 1.6, top="#f2d36b", side="#e0bd4a"))
    P["U3"] = (26, chip(12.8, 11.0, z, 1.8, 2.0, 0.8, 4, 0))
    P["RAA"] = (28, resistor(16.0, 11.65, z, ["#7a4a1e", "#3fa34d", "#c24"]))
    P["CAA"] = (31, box(19.6, 11.65, z, 1.0, 0.7, 0.6, "#e8c99a", "#d8b47d", "#c9a36a"))
    P["U2"] = (36, chip(24.0, 9.0, z, 5.6, 5.6, 0.9, 7, 7, "MCU"))
    P["RRST"] = (24, resistor(3.6, 18.2, z, ["#7a4a1e", "#111", "#e07a2e"]))
    P["CRST"] = (27, box(7.4, 18.2, z, 1.0, 0.7, 0.6, "#e8c99a", "#d8b47d", "#c9a36a"))
    P["SW1"] = (31, box(10.0, 17.6, z, 2.0, 2.0, 0.7) + cyl(11.0, 18.6, z + 0.7, 0.55, 0.5, top="#3c3c39", side="#2d2d2a"))
    P["RLED"] = (37, resistor(16.4, 19.2, z, ["#c24", "#c24", "#7a4a1e"]))
    P["DLED"] = (41, led(20.6, 19.55, z, "#ef6b62", "glowRed"))
    P["RSDA"] = (50, resistor(32.0, 17.2, z, ["#d9b236", "#7a3fbf", "#c24"]))
    P["RSCL"] = (53, resistor(32.0, 19.6, z, ["#d9b236", "#7a3fbf", "#c24"]))
    P["J2"] = (58, box(34.9, 21.6, z, 3.4, 0.8, 0.6, "#4a4a46", "#3a3a37", "#2e2e2b", stroke="#222")
               + "".join(box(34.95 + i * 0.85, 21.9, z + 0.6, 0.25, 0.25, 1.6, "#f0d77a", "#dcbf55", "#cdae44", sw=0.4) for i in range(4)))
    out = []
    for pid, (_, art) in sorted(P.items(), key=lambda kv: kv[1][0]):
        name, nl, role, check, bug = INFO[pid]
        out.append(f'<g class="apart" tabindex="0" data-id="{pid}" data-nl="{" ".join(nl)}"><title>{html.escape(name)}</title>{art}</g>')
    return "".join(out)


def art_svg() -> str:
    w, d, h = PLATE
    defs = ('<defs><radialGradient id="glowGreen"><stop offset="0" stop-color="#5fe07a" stop-opacity=".75"/><stop offset="1" stop-color="#5fe07a" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="glowRed"><stop offset="0" stop-color="#ff5a4e" stop-opacity=".75"/><stop offset="1" stop-color="#ff5a4e" stop-opacity="0"/></radialGradient>'
            '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2"/></filter></defs>')
    plate = box(0, 0, 0, w, d, h, "#f7f7f3", "#e7e7e0", "#d8d8d0", sw=0.8)
    ticks = "".join(f'<line x1="{iso(t, d, h * 0.55)[0]:.1f}" y1="{iso(t, d, h * 0.55)[1]:.1f}" x2="{iso(t, d, h * (0.25 if t % 5 else 0.05))[0]:.1f}" '
                    f'y2="{iso(t, d, h * (0.25 if t % 5 else 0.05))[1]:.1f}" stroke="{INK}" stroke-width=".6"/>' for t in range(1, int(w)))
    tag = box(1.0, 21.6, h, 6.5, 2.0, 0.05, "#ffffff", "#ececec", "#e0e0e0", sw=0.5)
    tx, ty = iso(4.2, 22.6, h + 0.05)
    tag += f'<text x="{tx:.1f}" y="{ty + 3:.1f}" text-anchor="middle" class="figtag">Fig. 1 · sensor circuit</text>'
    wires = []
    for net, line in routes():
        p = pts(iso(x, y, h + 0.02) for x, y in line)
        wires.append(f'<polyline class="wire {net}" points="{p}" fill="none"/>')
        if net in ("usb", "v33", "sig"):
            wires.append(f'<polyline class="glow {net}" points="{p}" fill="none" filter="url(#soft)"/>'
                         f'<polyline class="flow {net}" points="{p}" fill="none"/>')
    for pin in NETS["0"]:  # ground marks: a small via with a ring
        gx, gy = iso(*PINS[pin], h + 0.02)
        wires.append(f'<ellipse cx="{gx:.1f}" cy="{gy:.1f}" rx="4" ry="2.4" fill="none" stroke="{INK}" stroke-width=".8"/>'
                     f'<ellipse cx="{gx:.1f}" cy="{gy:.1f}" rx="1.8" ry="1.1" fill="{INK}"/>')
    for x, y in {PINS[p] for net, pins in NETS.items() if net != "0" for p in pins}:  # solder points
        px, py = iso(x, y, h + 0.02)
        wires.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.6" fill="{INK}"/>')
    notes = []  # Anatomy-style annotations: a short leader line up from the part, then a label
    for (x, y, zz), text in (((2.0, 4.6, 1.8), "USB 5 V"), ((9.0, 2.4, 3.1), "LM317 → 3.3 V"), ((5.0, 12.0, 0.8), "NTC sensor"),
                             ((13.7, 12.0, 1.0), "op-amp buffer"), ((20.1, 12.0, 0.7), "1 kHz filter"), ((11.0, 18.6, 1.3), "reset"),
                             ((25.3, 3.35, 1.1), "power LED"), ((20.6, 19.55, 1.1), "status LED"), ((36.4, 22.0, 2.3), "I²C")):
        x0, y0 = iso(x, y, h + zz)
        notes.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x0:.1f}" y2="{y0 - 22:.1f}" stroke="{INK}" stroke-width=".6"/>'
                     f'<text x="{x0 + 3:.1f}" y="{y0 - 25:.1f}" class="note">{html.escape(text)}</text>')
    width, height = iso(w, 0)[0] + 30, iso(w, d)[1] + 30
    return (f'<svg class="art" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Illustration of the sensor circuit">'
            f'{defs}{plate}{ticks}{tag}{"".join(wires)}{parts_svg(h)}{"".join(notes)}</svg>')


CSS = """.art{width:100%;height:auto} .art .apart{cursor:pointer;outline:none;transition:opacity .2s}
.art .apart:hover polygon,.art .apart:hover path,.art .apart:hover ellipse{filter:brightness(1.06)}
.art .wire{stroke:#9a9a90;stroke-width:1.1} .art .glow{stroke-width:5;opacity:.35} .art .flow{stroke-width:1.6;stroke-dasharray:3 9;animation:flow 1.6s linear infinite}
.art .usb.glow,.art .usb.flow{stroke:#8f6bff} .art .v33.glow,.art .v33.flow{stroke:#3d8bff} .art .sig.glow,.art .sig.flow{stroke:#ff8a2a}
@keyframes flow{to{stroke-dashoffset:-24}} .art .chiptext{font:600 11px Inter,sans-serif;fill:#d8d8d2}
.art .note{font:600 10px Inter,sans-serif;fill:#45453f;paint-order:stroke;stroke:#f7f7f3;stroke-width:3px} .art .figtag{font:600 8.5px Inter,sans-serif;fill:#5f5f58;letter-spacing:.04em}
.art.dim .apart{opacity:.35} .art.dim .apart.lit{opacity:1;filter:drop-shadow(0 0 6px #ffb347) drop-shadow(0 0 12px #ffb34799)}
.art .ledglow{animation:pulse 2.4s ease-in-out infinite} @keyframes pulse{50%{opacity:.55}}
@media (prefers-reduced-motion:reduce){.art .flow,.art .ledglow{animation:none}}"""
