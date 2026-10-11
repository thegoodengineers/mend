from amaranth import Cat, Elaboratable, Module, Signal


class BinToGray(Elaboratable):
    """Combinational binary to Gray code: gray = bin ^ (bin >> 1)."""

    def __init__(self, width: int):
        self.width = width
        self.bin = Signal(width)
        self.gray = Signal(width)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.gray.eq(self.bin ^ (self.bin >> 1))
        return m


class GrayToBin(Elaboratable):
    """Combinational Gray code to binary: bin[i] = XOR of gray[i:] (from the top bit down)."""

    def __init__(self, width: int):
        self.width = width
        self.gray = Signal(width)
        self.bin = Signal(width)

    def elaborate(self, platform):
        m = Module()
        bits = [None] * self.width
        bits[self.width - 1] = self.gray[self.width - 1]
        for i in range(self.width - 2, -1, -1):
            bits[i] = bits[i + 1] ^ self.gray[i]
        m.d.comb += self.bin.eq(Cat(*bits))
        return m
