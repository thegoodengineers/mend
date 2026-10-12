from amaranth import Elaboratable, Module, Signal

from hwlib.fifo import SyncFIFO
from hwlib.uart import UartTx

from .uart_rx import UartRx


class UartEcho(Elaboratable):
    """Echoes every byte received on rx back out on tx, through a FIFO: hwkit's UartRx feeding
    hwlib's SyncFIFO feeding hwlib's UartTx, all at the same `divisor`.

    Inputs:  rx
    Outputs: tx, overflow (one cycle when a byte arrives while the FIFO is full; that byte is lost),
             frame_err (from the receiver)
    """

    def __init__(self, divisor: int, depth: int = 16):
        self.divisor, self.depth = divisor, depth
        self.rx = Signal(init=1)
        self.tx = Signal(init=1)
        self.overflow = Signal()
        self.frame_err = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.urx = urx = UartRx(self.divisor)
        m.submodules.fifo = fifo = SyncFIFO(8, self.depth)
        m.submodules.utx = utx = UartTx(self.divisor)
        m.d.comb += [
            urx.rx.eq(self.rx),
            fifo.w_en.eq(urx.valid),
            fifo.w_data.eq(urx.data),
            self.overflow.eq(urx.valid & fifo.full),
            self.frame_err.eq(urx.frame_err),
            utx.data.eq(fifo.r_data),
            utx.start.eq(~fifo.empty & ~utx.busy),
            fifo.r_en.eq(~fifo.empty & ~utx.busy),  # UartTx samples data on this same edge
            self.tx.eq(utx.tx),
        ]
        return m
