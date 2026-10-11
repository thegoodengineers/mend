"""A small circuit simulator for netlists (the text form of a schematic): DC operating point and AC sweep.

Modified Nodal Analysis (Ho, Ruehli and Brennan, 1975), the method SPICE is built on, solved with
Gaussian elimination in plain Python. Netlist lines, SPICE style (node 0 is ground, `*` starts a comment):

    R<name> n1 n2 <ohms>              resistor
    C<name> n1 n2 <farads>            capacitor (open at DC)
    V<name> n+ n- DC <volts>          DC voltage source
    V<name> n+ n- AC <volts>          AC voltage source (0 V at DC)
    E<name> o+ o- i+ i- <gain>        voltage-controlled voltage source (an op-amp is E with gain 1e6)
    D<name> anode cathode VF=<volts>  LED or diode: drops VF when forward biased, blocks reverse current

Values take SPICE suffixes: f p n u m k meg g (`10k`, `100n`, `1meg`).
"""

import math
from pathlib import Path

SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9}


def value(text: str) -> float:
    t = text.strip().lower()
    for suffix in ("meg", "f", "p", "n", "u", "m", "k", "g"):
        if t.endswith(suffix):
            return float(t[: -len(suffix)]) * SUFFIX[suffix]
    return float(t)


class Circuit:
    def __init__(self, text: str):
        self.parts = []
        for raw in text.splitlines():
            line = raw.split("*", 1)[0].strip()
            if line:
                self.parts.append(line.split())
        self.nodes = sorted({n for p in self.parts for n in self._nets(p)} - {"0"})

    @staticmethod
    def _nets(p):
        return p[1:5] if p[0][0].upper() == "E" else p[1:3]

    def with_value(self, name: str, new: str) -> "Circuit":
        """A copy with one component's value changed (e.g. a switch resistor closed)."""
        c = Circuit("")
        c.parts = [p[:-1] + [new] if p[0] == name else list(p) for p in self.parts]
        c.nodes = self.nodes
        return c

    def _solve(self, omega: float, ac: bool, diode_on: dict) -> tuple[dict, dict]:
        idx = {n: i for i, n in enumerate(self.nodes)}
        branches = [p[0] for p in self.parts if p[0][0].upper() in "VE" or (p[0][0].upper() == "D" and diode_on[p[0]])]
        size = len(idx) + len(branches)
        a = [[0j] * size for _ in range(size)]
        b = [0j] * size

        def stamp_y(n1, n2, y):
            for x, s in ((n1, 1), (n2, -1)):
                for z, t in ((n1, 1), (n2, -1)):
                    if x != "0" and z != "0":
                        a[idx[x]][idx[z]] += s * t * y

        def stamp_source(row, plus, minus, volts):
            for n, s in ((plus, 1), (minus, -1)):
                if n != "0":
                    a[idx[n]][row] += s
                    a[row][idx[n]] += s
            b[row] += volts

        row = len(idx)
        for p in self.parts:
            kind, name = p[0][0].upper(), p[0]
            if kind == "R":
                stamp_y(p[1], p[2], 1 / value(p[3]))
            elif kind == "C":
                stamp_y(p[1], p[2], 1j * omega * value(p[3]))
            elif kind == "V":
                mode, volts = p[3].upper(), value(p[4])
                stamp_source(row, p[1], p[2], volts if (mode == "AC") == ac else 0)
                row += 1
            elif kind == "E":
                gain = value(p[5])
                stamp_source(row, p[1], p[2], 0)
                for n, s in ((p[3], 1), (p[4], -1)):
                    if n != "0":
                        a[row][idx[n]] -= s * gain
                row += 1
            elif kind == "D" and diode_on[name]:
                vf = value(p[3].split("=", 1)[1])
                stamp_source(row, p[1], p[2], 0 if ac else vf)
                row += 1
        x = _gauss(a, b)
        volts = {n: x[i] for n, i in idx.items()}
        volts["0"] = 0j
        currents = {name: x[len(idx) + k] for k, name in enumerate(branches)}
        return volts, currents

    def dc(self) -> "Result":
        """DC operating point. Diodes start on and are switched off while their current is negative."""
        diodes = [p[0] for p in self.parts if p[0][0].upper() == "D"]
        on = {d: True for d in diodes}
        for _ in range(len(diodes) + 1):
            volts, currents = self._solve(0.0, False, on)
            reversed_ = [d for d in diodes if on[d] and currents[d].real < 0]
            if not reversed_:
                break
            for d in reversed_:
                on[d] = False
        return Result(volts, currents)

    def ac(self, freq: float) -> "Result":
        """Small-signal response at `freq` Hz to the AC sources (diode states taken from the DC point)."""
        on = {d: abs(self.dc().i(d)) > 0 for d in (p[0] for p in self.parts if p[0][0].upper() == "D")}
        return Result(*self._solve(2 * math.pi * freq, True, on))


class Result:
    def __init__(self, volts: dict, currents: dict):
        self.volts, self.currents = volts, currents

    def v(self, node: str) -> float:
        """Real voltage at a node (DC)."""
        return self.volts[node].real

    def phasor(self, node: str) -> complex:
        return self.volts[node]

    def gain_db(self, out: str, inp: str) -> float:
        return 20 * math.log10(abs(self.volts[out]) / abs(self.volts[inp]))

    def i(self, name: str) -> float:
        """Current delivered by a source (out of its + terminal), or through a conducting diode anode to cathode (0 if off)."""
        c = self.currents.get(name, 0j)
        return -c.real if name[0].upper() in "VE" else c.real  # sources: current delivered out of +


def _gauss(a, b):
    n = len(b)
    a = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-15:
            raise ValueError("singular circuit: a node is floating or two sources fight")
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(col + 1, n):
            f = a[r][col] / a[col][col]
            if f:
                for c in range(col, n + 1):
                    a[r][c] -= f * a[col][c]
    x = [0j] * n
    for r in range(n - 1, -1, -1):
        x[r] = (a[r][n] - sum(a[r][c] * x[c] for c in range(r + 1, n))) / a[r][r]
    return x


def load(name: str) -> Circuit:
    return Circuit((Path(__file__).parent / f"{name}.cir").read_text(encoding="utf-8"))

