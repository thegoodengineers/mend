from amaranth import Elaboratable, Module, Signal


class ModCounter(Elaboratable):
    """Counts 0, 1, ..., modulus-1, 0, ... on every clock edge where `en` is high.

    Inputs:  en
    Outputs: count (0 .. modulus-1), wrap (combinational: high in the cycle where en is high and
             count is modulus-1, i.e. the cycle before count returns to 0)
    """

    def __init__(self, modulus: int):
        if modulus < 2:
            raise ValueError("modulus must be at least 2")
        self.modulus = modulus
        self.en = Signal()
        self.count = Signal(range(modulus))
        self.wrap = Signal()

    def elaborate(self, platform):
        m = Module()
        last = self.count == self.modulus - 1
        m.d.comb += self.wrap.eq(self.en & last)
        with m.If(self.en):
            with m.If(last):
                m.d.sync += self.count.eq(0)
            with m.Else():
                m.d.sync += self.count.eq(self.count + 1)
        return m
