from amaranth import Cat, Elaboratable, Module, Signal


class SpiMaster(Elaboratable):
    """SPI master, mode 0 (CPOL=0, CPHA=0), 8-bit transfers, most significant bit first.

    Inputs:  start (pulse; ignored while busy), tx_data (8 bits, sampled when a transfer starts),
             miso
    Outputs: sclk (idle low), mosi, cs_n (low for the whole transfer), busy,
             rx_data (8 bits, the byte read during the last transfer), done (one cycle at the end)
    sclk spends `half_period` clock cycles low, then `half_period` high, per bit. mosi changes on
    falling edges (and when cs_n drops); miso is sampled on rising edges.
    """

    def __init__(self, half_period: int):
        if half_period < 1:
            raise ValueError("half_period must be at least 1")
        self.half_period = half_period
        self.start = Signal()
        self.tx_data = Signal(8)
        self.miso = Signal()
        self.sclk = Signal()
        self.mosi = Signal()
        self.cs_n = Signal(init=1)
        self.busy = Signal()
        self.rx_data = Signal(8)
        self.done = Signal()

    def elaborate(self, platform):
        m = Module()
        out_shift = Signal(8)
        in_shift = Signal(8)
        bits_left = Signal(range(9))
        timer = Signal(range(self.half_period))
        m.d.comb += [self.busy.eq(bits_left != 0), self.mosi.eq(out_shift[7])]
        m.d.sync += self.done.eq(0)
        with m.If(~self.busy & self.start):
            m.d.sync += [out_shift.eq(self.tx_data), bits_left.eq(8), timer.eq(self.half_period - 1),
                         self.cs_n.eq(0), self.sclk.eq(0)]
        with m.Elif(self.busy):
            with m.If(timer != 0):
                m.d.sync += timer.eq(timer - 1)
            with m.Elif(~self.sclk):  # rising edge: sample
                m.d.sync += [self.sclk.eq(1), in_shift.eq(Cat(self.miso, in_shift[:7])),
                             timer.eq(self.half_period - 1)]
            with m.Else():  # falling edge: next bit out, or finish
                m.d.sync += [self.sclk.eq(0), out_shift.eq(out_shift << 1), bits_left.eq(bits_left - 1),
                             timer.eq(self.half_period - 1)]
                with m.If(bits_left == 1):
                    m.d.sync += [self.cs_n.eq(1), self.rx_data.eq(in_shift), self.done.eq(1)]
        return m
