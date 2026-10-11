from simhelp import simulate

from hwlib.counter import ModCounter


def run_counter(modulus, enables):
    dut = ModCounter(modulus)
    seen = []

    async def bench(ctx):
        for en in enables:
            ctx.set(dut.en, en)
            seen.append((ctx.get(dut.count), ctx.get(dut.wrap)))
            await ctx.tick()

    simulate(dut, bench)
    return seen


def test_counts_up_and_wraps_at_modulus():
    seen = run_counter(10, [1] * 23)
    assert [c for c, _ in seen] == [i % 10 for i in range(23)]


def test_wrap_pulses_in_the_last_cycle_only():
    seen = run_counter(4, [1] * 9)
    assert [w for _, w in seen] == [0, 0, 0, 1, 0, 0, 0, 1, 0]


def test_holds_when_disabled():
    seen = run_counter(5, [1, 1, 0, 0, 1, 0, 1])
    assert [c for c, _ in seen] == [0, 1, 2, 2, 2, 3, 3]
    assert all(w == 0 for _, w in seen)
