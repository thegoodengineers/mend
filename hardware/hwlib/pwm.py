from amaranth import Elaboratable, Module, Signal


class PWM(Elaboratable):
    """Pulse-width modulator with a fixed period.

    Inputs:  duty (0 .. period): how many cycles of each period the output is high
    Outputs: out. duty 0 is always low, duty == period is always high.
    The internal phase counter runs 0 .. period-1 and wraps; out = phase < duty.
    """

    def __init__(self, period: int):
        if period < 2:
            raise ValueError("period must be at least 2")
        self.period = period
        self.duty = Signal(range(period + 1))
        self.out = Signal()

    def elaborate(self, platform):
        m = Module()
        phase = Signal(range(self.period))
        with m.If(phase == self.period - 1):
            m.d.sync += phase.eq(0)
        with m.Else():
            m.d.sync += phase.eq(phase + 1)
        m.d.comb += self.out.eq(phase < self.duty)
        return m
