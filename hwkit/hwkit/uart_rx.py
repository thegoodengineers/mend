from amaranth import Cat, Elaboratable, Module, Signal


class UartRx(Elaboratable):
    """UART receiver, 8N1: the counterpart of hwlib.uart.UartTx with the same `divisor`.

    Inputs:  rx (line, idle high; asynchronous, passed through a two-flip-flop synchroniser)
    Outputs: data (8 bits, the last good byte), valid (one cycle when a byte with a good stop bit
             arrives), frame_err (one cycle when the stop bit reads 0), busy (inside a frame)
    Each bit is sampled once, in its middle. A start bit that is gone by its middle is a glitch and
    is ignored. After a framing error (e.g. a break) the receiver waits for the line to go idle.
    Tolerates a baud mismatch of a few percent (about 5% at large divisors).
    Latency: valid rises 2 + divisor // 2 + 9 * divisor clock edges after the edge that first sees
    the start bit on rx (2 for the synchroniser, then the middle of the stop bit).
    """

    def __init__(self, divisor: int):
        if divisor < 2:
            raise ValueError("divisor must be at least 2 (one sample in the middle of each bit)")
        self.divisor = divisor
        self.rx = Signal(init=1)
        self.data = Signal(8)
        self.valid = Signal()
        self.frame_err = Signal()
        self.busy = Signal()

    def elaborate(self, platform):
        m = Module()
        meta = Signal(init=1)
        line = Signal(init=1)
        m.d.sync += [meta.eq(self.rx), line.eq(meta)]

        timer = Signal(range(self.divisor))
        bit = Signal(range(8))
        shift = Signal(8)
        tick = timer == 0
        with m.If(~tick):
            m.d.sync += timer.eq(timer - 1)
        m.d.sync += [self.valid.eq(0), self.frame_err.eq(0)]

        with m.FSM():
            with m.State("IDLE"):
                with m.If(~line):
                    m.d.sync += timer.eq(self.divisor // 2 - 1)  # land in the middle of the start bit
                    m.next = "START"
            with m.State("START"):
                m.d.comb += self.busy.eq(1)
                with m.If(tick):
                    with m.If(line):
                        m.next = "IDLE"  # glitch, not a start bit
                    with m.Else():
                        m.d.sync += [timer.eq(self.divisor - 1), bit.eq(0)]
                        m.next = "DATA"
            with m.State("DATA"):
                m.d.comb += self.busy.eq(1)
                with m.If(tick):
                    m.d.sync += [shift.eq(Cat(shift[1:], line)), timer.eq(self.divisor - 1)]
                    with m.If(bit == 7):
                        m.next = "STOP"
                    with m.Else():
                        m.d.sync += bit.eq(bit + 1)
            with m.State("STOP"):
                m.d.comb += self.busy.eq(1)
                with m.If(tick):
                    with m.If(line):
                        m.d.sync += [self.data.eq(shift), self.valid.eq(1)]
                        m.next = "IDLE"
                    with m.Else():
                        m.d.sync += self.frame_err.eq(1)
                        m.next = "BREAK"
            with m.State("BREAK"):
                with m.If(line):
                    m.next = "IDLE"
        return m
