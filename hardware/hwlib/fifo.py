from amaranth import Array, Elaboratable, Module, Signal


class SyncFIFO(Elaboratable):
    """Synchronous first-in first-out buffer.

    Inputs:  w_en, w_data (write on the clock edge when w_en is high and the FIFO is not full),
             r_en (drop the head on the clock edge when r_en is high and the FIFO is not empty)
    Outputs: r_data (the head entry, valid while not empty), level (entries stored),
             empty (level == 0), full (level == depth)
    A simultaneous read and write on a non-empty, non-full FIFO keeps the level the same.
    """

    def __init__(self, width: int, depth: int):
        if depth < 2 or depth & (depth - 1):
            raise ValueError("depth must be a power of two (pointers wrap by overflowing)")
        self.width, self.depth = width, depth
        self.w_en = Signal()
        self.w_data = Signal(width)
        self.r_en = Signal()
        self.r_data = Signal(width)
        self.level = Signal(range(depth + 1))
        self.empty = Signal()
        self.full = Signal()

    def elaborate(self, platform):
        m = Module()
        store = Array(Signal(self.width, name=f"slot{i}") for i in range(self.depth))
        w_ptr = Signal(range(self.depth))
        r_ptr = Signal(range(self.depth))
        m.d.comb += [
            self.empty.eq(self.level == 0),
            self.full.eq(self.level == self.depth),
            self.r_data.eq(store[r_ptr]),
        ]
        do_w = self.w_en & ~self.full
        do_r = self.r_en & ~self.empty
        with m.If(do_w):
            m.d.sync += store[w_ptr].eq(self.w_data)
            m.d.sync += w_ptr.eq(w_ptr + 1)
        with m.If(do_r):
            m.d.sync += r_ptr.eq(r_ptr + 1)
        with m.If(do_w & ~do_r):
            m.d.sync += self.level.eq(self.level + 1)
        with m.Elif(do_r & ~do_w):
            m.d.sync += self.level.eq(self.level - 1)
        return m
