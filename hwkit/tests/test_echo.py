from simhelp import simulate

from hwkit.echo import UartEcho


def bits_of(byte):
    return [0] + [(byte >> i) & 1 for i in range(8)] + [1]


def run_echo(data, divisor=4, depth=16, tail_frames=None):
    """Send `data` back to back into rx; decode everything that comes out of tx (by sampling the
    middle of each bit, like a terminal would). Returns (echoed bytes, overflow count)."""
    dut = UartEcho(divisor, depth)
    line = [1] * 4 + [b for byte in data for b in bits_of(byte) for _ in range(divisor)]
    tail = (tail_frames if tail_frames is not None else len(data) + 2) * 10 * divisor
    tx, overflows = [], 0

    async def bench(ctx):
        nonlocal overflows
        for level in line + [1] * tail:
            ctx.set(dut.rx, level)
            await ctx.tick()
            tx.append(ctx.get(dut.tx))
            overflows += ctx.get(dut.overflow)

    simulate(dut, bench)
    out, i = [], 0
    while i < len(tx):
        if tx[i] == 0:  # start bit
            mid = i + divisor // 2
            bits = [tx[mid + k * divisor] for k in range(10) if mid + k * divisor < len(tx)]
            if len(bits) < 10:
                break
            assert bits[0] == 0 and bits[9] == 1, "malformed frame on tx"
            out.append(sum(b << k for k, b in enumerate(bits[1:9])))
            i += 10 * divisor
        else:
            i += 1
    return out, overflows


def test_echoes_bytes_in_order():
    data = [0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x00, 0xFF]
    assert run_echo(data) == (data, 0)


def test_long_back_to_back_burst_through_a_small_fifo():
    # rx and tx run at the same bit rate; tx spends one extra cycle per frame starting up, so a
    # back-to-back burst builds a small backlog. A 2-entry FIFO must absorb it with nothing lost.
    data = list(range(20))
    echoed, overflows = run_echo(data, depth=2)
    assert overflows == 0 and echoed == data
