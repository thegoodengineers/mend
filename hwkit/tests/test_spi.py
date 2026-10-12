import pytest
from simhelp import simulate

from hwkit.spi import SpiMaster


def transfer(half_period, pairs):
    """pairs: (master byte, slave byte). A mode-0 slave model answers on miso and records mosi.
    Returns (bytes the master read, bytes the slave read, per-cycle (sclk, cs_n) trace)."""
    dut = SpiMaster(half_period)
    master_got, slave_got, trace = [], [], []

    async def bench(ctx):
        for tx, reply in pairs:
            ctx.set(dut.tx_data, tx)
            ctx.set(dut.start, 1)
            await ctx.tick()
            ctx.set(dut.start, 0)
            ctx.set(dut.tx_data, 0)  # sampled at start
            out, received, prev_sclk = reply, 0, 0
            ctx.set(dut.miso, (out >> 7) & 1)  # slave drives its first bit when cs_n drops
            for _ in range(16 * half_period + 4):
                sclk, cs_n = ctx.get(dut.sclk), ctx.get(dut.cs_n)
                trace.append((sclk, cs_n))
                if sclk and not prev_sclk:  # rising: slave samples mosi
                    received = (received << 1) | ctx.get(dut.mosi)
                if prev_sclk and not sclk:  # falling: slave shifts out its next bit
                    out = (out << 1) & 0xFF
                    ctx.set(dut.miso, (out >> 7) & 1)
                prev_sclk = sclk
                if ctx.get(dut.done):
                    master_got.append(ctx.get(dut.rx_data))
                    break
                await ctx.tick()
            slave_got.append(received)
            assert not ctx.get(dut.busy)

    simulate(dut, bench)
    return master_got, slave_got, trace


@pytest.mark.parametrize("half_period", [1, 2, 5])
def test_full_duplex_exchange(half_period):
    # none of these is a bit-palindrome, so a reversed bit order shows up
    pairs = [(0xA6, 0x1D), (0x00, 0xFF), (0xFF, 0x00), (0x83, 0x2B), (0x01, 0x80)]
    master_got, slave_got, _ = transfer(half_period, pairs)
    assert master_got == [reply for _, reply in pairs]
    assert slave_got == [tx for tx, _ in pairs]


def test_eight_clock_pulses_inside_chip_select():
    _, _, trace = transfer(3, [(0x5A, 0xC3)])
    rising = sum(1 for (a, _), (b, _) in zip(trace, trace[1:]) if b and not a)
    assert rising == 8
    assert all(cs == 0 for sclk, cs in trace if sclk)  # clock only toggles while selected
    assert trace[-1][0] == 0  # clock back low at the end


def test_idle_state():
    dut = SpiMaster(2)
    seen = []

    async def bench(ctx):
        for _ in range(5):
            seen.append((ctx.get(dut.sclk), ctx.get(dut.cs_n), ctx.get(dut.busy)))
            await ctx.tick()

    simulate(dut, bench)
    assert seen == [(0, 1, 0)] * 5


def test_start_while_busy_is_ignored():
    dut = SpiMaster(1)
    done = []

    async def bench(ctx):
        ctx.set(dut.tx_data, 0x11)
        ctx.set(dut.start, 1)  # held high: must not restart mid-transfer
        for _ in range(17):
            await ctx.tick()
            done.append(ctx.get(dut.done))

    simulate(dut, bench)
    assert done.index(1) == 16  # one full 16-cycle transfer, not cut short


def test_rejects_zero_half_period():
    with pytest.raises(ValueError):
        SpiMaster(0)
