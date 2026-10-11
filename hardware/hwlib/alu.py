from amaranth import Elaboratable, Module, Signal

ADD, SUB, AND, OR, XOR = range(5)


class ALU(Elaboratable):
    """Combinational 8-bit ALU.

    Inputs:  a, b (8 bits), op (ADD, SUB, AND, OR, XOR)
    Outputs: result (8 bits, wraps around), zero (result == 0),
             carry (ADD: carry out of bit 7; SUB: 1 when a < b, i.e. a borrow; logic ops: 0)
    SUB computes a - b.
    """

    def __init__(self):
        self.a = Signal(8)
        self.b = Signal(8)
        self.op = Signal(3)
        self.result = Signal(8)
        self.zero = Signal()
        self.carry = Signal()

    def elaborate(self, platform):
        m = Module()
        wide = Signal(9)
        with m.Switch(self.op):
            with m.Case(ADD):
                m.d.comb += wide.eq(self.a + self.b)
                m.d.comb += self.carry.eq(wide[8])
            with m.Case(SUB):
                m.d.comb += wide.eq(self.a - self.b)
                m.d.comb += self.carry.eq(self.a < self.b)
            with m.Case(AND):
                m.d.comb += wide.eq(self.a & self.b)
            with m.Case(OR):
                m.d.comb += wide.eq(self.a | self.b)
            with m.Case(XOR):
                m.d.comb += wide.eq(self.a ^ self.b)
        m.d.comb += [self.result.eq(wide[:8]), self.zero.eq(wide[:8] == 0)]
        return m
