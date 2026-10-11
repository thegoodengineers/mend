"""Draw the schematic transfer test's circuits as SVG schematics -> docs/img/schematics/<name>.svg

    python scripts/draw_schematics.py      (needs: pip install schemdraw==0.19)

Values in the labels are the correct design values from schematics/circuits/*.cir.
"""

from pathlib import Path

import schemdraw
import schemdraw.elements as elm

OUT = Path(__file__).resolve().parent.parent / "docs" / "img" / "schematics"
schemdraw.use("svg")


def divider(d):
    elm.SourceV().up().label("V1 5 V")
    elm.Resistor().right().label("R1 10k")
    d.push()
    elm.Resistor().down().label("R2 20k", loc="bottom")
    elm.Line().left()
    elm.Ground()
    d.pop()
    elm.Line().right().length(1.5)
    elm.Dot(open=True).label("out  3.3 V", loc="right")


def led(d):
    elm.SourceV().up().label("V1 5 V")
    elm.Resistor().right().label("R1 300")
    elm.LED().down().label("D1 red\nVf 2.0 V\n10 mA", loc="bottom")
    elm.Line().left()
    elm.Ground()


def rc(d, high: bool):
    elm.SourceSin().up().label("in")
    (elm.Capacitor() if high else elm.Resistor()).right().label("C1 159n" if high else "R1 1.59k")
    d.push()
    (elm.Resistor() if high else elm.Capacitor()).down().label("R1 1k" if high else "C1 100n", loc="bottom")
    elm.Line().left()
    elm.Ground()
    d.pop()
    elm.Line().right().length(1.5)
    elm.Dot(open=True).label("out  fc = 1 kHz", loc="right")


def noninv(d):
    op = elm.Opamp(leads=True)
    elm.Line().left().at(op.in2).length(1)
    elm.Dot(open=True).label("in  0.1 V", loc="left")
    elm.Line().up().at(op.in1).length(1.6)
    d.push()
    elm.Resistor().tox(op.out).label("RF 100k")
    elm.Line().toy(op.out).dot()
    d.pop()
    elm.Resistor().left().at(op.in1).label("RG 10k", loc="bottom")
    elm.Ground()
    elm.Line().right().at(op.out).length(1)
    elm.Dot(open=True).label("out  1.1 V (gain 11)", loc="right")


def inverting(d):
    op = elm.Opamp(leads=True)
    elm.Line().down().at(op.in2).length(0.6)
    elm.Ground(lead=False)
    elm.Resistor().left().at(op.in1).label("RIN 10k", loc="bottom")
    elm.Dot(open=True).label("in  0.2 V", loc="left")
    elm.Line().up().at(op.in1).length(1.6)
    elm.Resistor().tox(op.out).label("RF 47k")
    elm.Line().toy(op.out).dot()
    elm.Line().right().at(op.out).length(1)
    elm.Dot(open=True).label("out  -0.94 V (gain -4.7)", loc="right")


def pullup(d):
    src = elm.SourceV().up().label("3.3 V")
    elm.Ground().at(src.start)
    elm.Line().right().at(src.end).length(1.5)
    elm.Resistor().down().label("RPU 10k", loc="bottom")
    elm.Dot()
    d.push()
    elm.Line().right().length(2)
    elm.Dot(open=True).label("MCU input pin", loc="right")
    d.pop()
    elm.Button().down().label("button", loc="bottom")
    elm.Ground()


CIRCUITS = {"divider": divider, "led": led, "lowpass": lambda d: rc(d, False), "highpass": lambda d: rc(d, True),
            "noninv": noninv, "inverting": inverting, "pullup": pullup}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in CIRCUITS.items():
        with schemdraw.Drawing(show=False) as d:
            d.config(unit=2.6, fontsize=13, font="Inter, Arial, sans-serif", lw=1.4)
            draw(d)
            (OUT / f"{name}.svg").write_bytes(d.get_imagedata("svg"))
        print("wrote", OUT / f"{name}.svg")
