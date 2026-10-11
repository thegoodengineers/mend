from amaranth import Cat, Const, Elaboratable, Module, Mux, Signal


class UartTx(Elaboratable):
    """UART transmitter, 8N1: a start bit (0), 8 data bits least significant first, a stop bit (1).

    Inputs:  start (pulse; ignored while busy), data (8 bits, sampled when a frame starts)
    Outputs: tx (line, 1 when idle), busy (high while a frame is being sent)
    Every bit is held on tx for `divisor` clock cycles.
    """

    def __init__(self, divisor: int):
        if divisor < 1:
            raise ValueError("divisor must be at least 1")
        self.divisor = divisor
        self.start = Signal()
        self.data = Signal(8)
        self.tx = Signal(init=1)
        self.busy = Signal()

    def elaborate(self, platform):
        m = Module()
        frame = Signal(10)
        bits_left = Signal(range(11))
        timer = Signal(range(self.divisor))
        m.d.comb += [self.busy.eq(bits_left != 0), self.tx.eq(Mux(self.busy, frame[0], 1))]
        with m.If(~self.busy & self.start):
            m.d.sync += [frame.eq(Cat(Const(0, 1), self.data, Const(1, 1))),
                         bits_left.eq(10), timer.eq(self.divisor - 1)]
        with m.Elif(self.busy):
            with m.If(timer == 0):
                m.d.sync += [frame.eq(frame >> 1), bits_left.eq(bits_left - 1), timer.eq(self.divisor - 1)]
            with m.Else():
                m.d.sync += timer.eq(timer - 1)
        return m
