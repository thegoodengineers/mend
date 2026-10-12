from amaranth import Elaboratable, Module, Signal


class EdgeDetect(Elaboratable):
    """Synchronises an asynchronous input and flags its edges.

    Inputs:  raw (asynchronous: may change at any time, e.g. a pin)
    Outputs: level (raw after a two-flip-flop synchroniser, so 2 cycles late; starts at `init`),
             rise (high for one cycle when level goes 0 -> 1), fall (one cycle when level goes 1 -> 0)
    """

    def __init__(self, init: int = 0):
        self.init = init
        self.raw = Signal(init=init)
        self.level = Signal(init=init)
        self.rise = Signal()
        self.fall = Signal()

    def elaborate(self, platform):
        m = Module()
        meta = Signal(init=self.init)
        prev = Signal(init=self.init)
        m.d.sync += [meta.eq(self.raw), self.level.eq(meta), prev.eq(self.level)]
        m.d.comb += [self.rise.eq(self.level & ~prev), self.fall.eq(~self.level & prev)]
        return m
