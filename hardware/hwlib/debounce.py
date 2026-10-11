from amaranth import Elaboratable, Module, Signal


class Debouncer(Elaboratable):
    """Debounces a noisy input (for example a push button).

    Inputs:  raw
    Outputs: out (starts at 0). out takes raw's value only after raw has differed from out on
             `cycles` consecutive clock edges; any bounce back to out's value restarts the count.
    """

    def __init__(self, cycles: int):
        if cycles < 1:
            raise ValueError("cycles must be at least 1")
        self.cycles = cycles
        self.raw = Signal()
        self.out = Signal()

    def elaborate(self, platform):
        m = Module()
        count = Signal(range(self.cycles + 1))
        with m.If(self.raw == self.out):
            m.d.sync += count.eq(0)
        with m.Elif(count == self.cycles - 1):
            m.d.sync += [self.out.eq(self.raw), count.eq(0)]
        with m.Else():
            m.d.sync += count.eq(count + 1)
        return m
