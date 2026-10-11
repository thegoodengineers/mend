from simhelp import settle, simulate

from hwlib.gray import BinToGray, GrayToBin


def gray(n):
    return n ^ (n >> 1)


def test_bin_to_gray_all_6_bit_values():
    dut = BinToGray(6)
    out = {}

    async def bench(ctx):
        for n in range(64):
            ctx.set(dut.bin, n)
            await settle(ctx)
            out[n] = ctx.get(dut.gray)

    simulate(dut, bench, clock=False)
    assert out == {n: gray(n) for n in range(64)}


def test_gray_to_bin_inverts_bin_to_gray():
    dut = GrayToBin(6)
    out = {}

    async def bench(ctx):
        for n in range(64):
            ctx.set(dut.gray, gray(n))
            await settle(ctx)
            out[n] = ctx.get(dut.bin)

    simulate(dut, bench, clock=False)
    assert out == {n: n for n in range(64)}


def test_adjacent_gray_codes_differ_in_one_bit():
    assert all(bin(gray(n) ^ gray(n + 1)).count("1") == 1 for n in range(63))
