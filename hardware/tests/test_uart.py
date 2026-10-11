from simhelp import simulate

from hwlib.uart import UartTx


def capture(divisor, byte, idle_after=5):
    """Pulse start for one cycle and record tx and busy on every cycle until the frame is done."""
    dut = UartTx(divisor)
    tx, busy = [], []

    async def bench(ctx):
        ctx.set(dut.data, byte)
        tx.append(ctx.get(dut.tx))
        ctx.set(dut.start, 1)
        await ctx.tick()
        ctx.set(dut.start, 0)
        ctx.set(dut.data, 0)  # data is sampled at start; changing it now must not matter
        for _ in range(10 * divisor + idle_after):
            tx.append(ctx.get(dut.tx))
            busy.append(ctx.get(dut.busy))
            await ctx.tick()

    simulate(dut, bench)
    return tx, busy


def expected_bits(byte):
    return [0] + [(byte >> i) & 1 for i in range(8)] + [1]


def test_idle_line_is_high():
    tx, _ = capture(2, 0x00)
    assert tx[0] == 1


def test_frame_is_start_lsb_first_stop():
    for byte in (0x01, 0x80, 0xA5, 0x3C):
        tx, _ = capture(1, byte)
        assert tx[1:11] == expected_bits(byte), hex(byte)


def test_each_bit_lasts_divisor_cycles():
    tx, _ = capture(3, 0x5A)
    sampled = [tx[1 + 3 * i + 1] for i in range(10)]  # middle of each bit
    assert sampled == expected_bits(0x5A)
    assert tx[1:31] == [b for b in expected_bits(0x5A) for _ in range(3)]


def test_busy_for_the_whole_frame_then_idle():
    _, busy = capture(2, 0xFF)
    assert busy[:20] == [1] * 20
    assert busy[20:] == [0] * 5
