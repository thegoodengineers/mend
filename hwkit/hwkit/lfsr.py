from amaranth import Cat, Elaboratable, Module, Signal

# Maximal-length Fibonacci taps (1-indexed bit positions), from Xilinx XAPP052.
# With XOR feedback and a nonzero seed each one cycles through all 2**n - 1 nonzero states.
TAPS = {
    3: (3, 2), 4: (4, 3), 5: (5, 3), 6: (6, 5), 7: (7, 6), 8: (8, 6, 5, 4), 9: (9, 5), 10: (10, 7),
    11: (11, 9), 12: (12, 6, 4, 1), 13: (13, 4, 3, 1), 14: (14, 5, 3, 1), 15: (15, 14),
    16: (16, 15, 13, 4), 17: (17, 14), 18: (18, 11), 19: (19, 6, 2, 1), 20: (20, 17),
    24: (24, 23, 22, 17), 31: (31, 28), 32: (32, 22, 2, 1),
}


def lfsr_step(state: int, width: int, taps) -> int:
    """Plain-Python reference: one shift of the register."""
    feedback = 0
    for t in taps:
        feedback ^= (state >> (t - 1)) & 1
    return ((state << 1) | feedback) & ((1 << width) - 1)


class LFSR(Elaboratable):
    """Fibonacci linear-feedback shift register (pseudo-random sequence, test patterns, scramblers).

    Inputs:  en (shift on the clock edge when high)
    Outputs: state (`width` bits, starts at `seed`), out (state's top bit)
    Each shift: state = (state << 1) | XOR of the tapped bits. With the default taps the sequence
    repeats after 2**width - 1 shifts. seed must not be 0 (0 is a fixed point).
    """

    def __init__(self, width: int, seed: int = 1, taps=None):
        if taps is None:
            if width not in TAPS:
                raise ValueError(f"no default taps for width {width}; pass taps= (known: {sorted(TAPS)})")
            taps = TAPS[width]
        if not taps or any(not 1 <= t <= width for t in taps):
            raise ValueError("taps must be bit positions 1..width")
        if not 0 < seed < (1 << width):
            raise ValueError("seed must be nonzero and fit in width bits")
        self.width, self.seed, self.taps = width, seed, tuple(taps)
        self.en = Signal()
        self.state = Signal(width, init=seed)
        self.out = Signal()

    def elaborate(self, platform):
        m = Module()
        feedback = 0
        for t in self.taps:
            feedback = feedback ^ self.state[t - 1]
        with m.If(self.en):
            m.d.sync += self.state.eq(Cat(feedback, self.state[:-1]))
        m.d.comb += self.out.eq(self.state[-1])
        return m
