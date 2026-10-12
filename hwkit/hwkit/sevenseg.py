from amaranth import Elaboratable, Module, Signal

# Segments as bits 0..6 = a, b, c, d, e, f, g (a on top, then clockwise, g in the middle).
GLYPHS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07,  # 0-7
          0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71]  # 8-9, A, b, C, d, E, F


class SevenSeg(Elaboratable):
    """Combinational hex digit to seven-segment decoder.

    Inputs:  digit (4 bits, 0-F), blank (all segments off)
    Outputs: segments (7 bits: bit 0 = a ... bit 6 = g). Lit = 1, or lit = 0 with active_low=True
             (common-anode displays).
    """

    def __init__(self, active_low: bool = False):
        self.active_low = active_low
        self.digit = Signal(4)
        self.blank = Signal()
        self.segments = Signal(7)

    def elaborate(self, platform):
        m = Module()
        lit = Signal(7)
        with m.If(~self.blank):
            with m.Switch(self.digit):
                for value, glyph in enumerate(GLYPHS):
                    with m.Case(value):
                        m.d.comb += lit.eq(glyph)
        m.d.comb += self.segments.eq(~lit if self.active_low else lit)
        return m
