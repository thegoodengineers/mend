from amaranth import Elaboratable, Module, Mux, Signal

POLY = 0x07  # CRC-8/SMBUS: x^8 + x^2 + x + 1, init 0, no reflection, no final xor


class Crc8Byte(Elaboratable):
    """Combinational CRC-8 update for one byte, most significant bit first.

    Inputs:  crc_in (8 bits, the running CRC; 0 to start), data (8 bits)
    Outputs: crc_out (8 bits). Chaining bytes of b"123456789" from 0 gives the standard check 0xF4.
    """

    def __init__(self):
        self.crc_in = Signal(8)
        self.data = Signal(8)
        self.crc_out = Signal(8)

    def elaborate(self, platform):
        m = Module()
        c = self.crc_in ^ self.data
        for _ in range(8):
            shifted = (c << 1)[:8]
            c = Mux(c[7], shifted ^ POLY, shifted)
        m.d.comb += self.crc_out.eq(c)
        return m
