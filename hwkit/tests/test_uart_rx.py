import pytest
from amaranth import Elaboratable, Module, Signal
from simhelp import simulate

from hwkit.uart_rx import UartRx
from hwlib.uart import UartTx


def frame_bits(byte, stop=1):
    return [0] + [(byte >> i) & 1 for i in range(8)] + [stop]


def drive(divisor, bits, bit_cycles=None, idle_before=3, idle_after=None):
    """Drive rx with `bits`, each held `bit_cycles` (default: divisor) cycles. Returns a list of
    ("byte", value) / ("err", None) events in order, plus the busy trace."""
    bit_cycles = bit_cycles or divisor
    idle_after = 3 * divisor if idle_after is None else idle_after
    dut = UartRx(divisor)
    events, busy = [], []
    line = [1] * idle_before + [b for b in bits for _ in range(bit_cycles)] + [1] * idle_after

    async def bench(ctx):
        for level in line:
            ctx.set(dut.rx, level)
            await ctx.tick()
            busy.append(ctx.get(dut.busy))
            if ctx.get(dut.valid):
                events.append(("byte", ctx.get(dut.data)))
            if ctx.get(dut.frame_err):
                events.append(("err", None))

    simulate(dut, bench)
    return events, busy


@pytest.mark.parametrize("divisor", [2, 3, 4, 8, 16])
def test_receives_every_byte_value_class(divisor):
    data = [0x00, 0xFF, 0x55, 0xAA, 0x01, 0x80, 0x3C]
    bits = [b for byte in data for b in frame_bits(byte)]
    events, _ = drive(divisor, bits)
    assert events == [("byte", d) for d in data]


def test_back_to_back_frames_without_idle_gap():
    bits = frame_bits(0x12) + frame_bits(0x34) + frame_bits(0x56)
    events, _ = drive(4, bits)
    assert events == [("byte", 0x12), ("byte", 0x34), ("byte", 0x56)]


def test_tolerates_three_percent_baud_mismatch():
    data = [0xA5, 0x0F, 0xF0]
    bits = [b for byte in data for b in frame_bits(byte)]
    for bit_cycles in (31, 33):  # receiver expects 32
        events, _ = drive(32, bits, bit_cycles=bit_cycles)
        assert events == [("byte", d) for d in data], bit_cycles


def test_short_glitch_is_not_a_start_bit():
    dut_divisor = 8
    events, busy = drive(dut_divisor, [0, 1, 1, 1], bit_cycles=2)  # 2-cycle low pulse
    assert events == []
    assert busy[-1] == 0


def test_bad_stop_bit_raises_frame_error_then_recovers():
    bits = frame_bits(0x42, stop=0) + [0] * 3 + [1] * 2 + frame_bits(0x99)  # break, then a good byte
    events, _ = drive(4, bits)
    assert events == [("err", None), ("byte", 0x99)]


def test_busy_only_inside_a_frame():
    _, busy = drive(4, frame_bits(0x5A), idle_before=3, idle_after=12)
    assert busy[:3] == [0, 0, 0]
    assert sum(busy) >= 9 * 4 and busy[-4:] == [0] * 4


@pytest.mark.parametrize("divisor", [2, 3, 8, 16])
def test_valid_latency_is_as_documented(divisor):
    dut = UartRx(divisor)
    line = [1] * 3 + [b for b in frame_bits(0x6A) for _ in range(divisor)] + [1] * 3 * divisor
    at = []

    async def bench(ctx):
        for i, level in enumerate(line):
            ctx.set(dut.rx, level)
            await ctx.tick()
            if ctx.get(dut.valid):
                at.append(i)

    simulate(dut, bench)
    assert [a - 3 for a in at] == [2 + divisor // 2 + 9 * divisor]


def test_rejects_divisor_below_two():
    with pytest.raises(ValueError):
        UartRx(1)


class Loopback(Elaboratable):
    def __init__(self, divisor):
        self.tx = UartTx(divisor)
        self.rx = UartRx(divisor)

    def elaborate(self, platform):
        m = Module()
        m.submodules.tx, m.submodules.rx = self.tx, self.rx
        m.d.comb += self.rx.rx.eq(self.tx.tx)
        return m


@pytest.mark.parametrize("divisor", [2, 5, 16])
def test_loopback_with_hwlib_transmitter(divisor):
    top = Loopback(divisor)
    data = [0x00, 0x7E, 0x81, 0xFF, 0x33]
    got = []

    async def bench(ctx):
        async def step():
            await ctx.tick()
            if ctx.get(top.rx.valid):
                got.append(ctx.get(top.rx.data))

        for byte in data:  # back to back: start the next frame as soon as the transmitter is free
            while ctx.get(top.tx.busy):
                await step()
            ctx.set(top.tx.data, byte)
            ctx.set(top.tx.start, 1)
            await step()
            ctx.set(top.tx.start, 0)
        for _ in range(12 * divisor + 4):
            await step()

    simulate(top, bench)
    assert got == data
