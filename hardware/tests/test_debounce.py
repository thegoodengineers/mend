from simhelp import simulate

from hwlib.debounce import Debouncer


def run(cycles, raw_seq):
    dut = Debouncer(cycles)
    out = []

    async def bench(ctx):
        for raw in raw_seq:
            ctx.set(dut.raw, raw)
            out.append(ctx.get(dut.out))
            await ctx.tick()
        out.append(ctx.get(dut.out))

    simulate(dut, bench)
    return out


def model(cycles, raw_seq):
    state, count, out = 0, 0, []
    for raw in raw_seq:
        out.append(state)
        if raw == state:
            count = 0
        elif count == cycles - 1:
            state, count = raw, 0
        else:
            count += 1
    return out + [state]


def test_clean_press_changes_after_n_cycles():
    seq = [0, 0] + [1] * 8
    assert run(4, seq) == model(4, seq)
    assert run(4, seq)[-1] == 1


def test_bouncing_never_reaches_the_output():
    seq = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0] * 3  # never 4 ones in a row
    assert run(4, seq) == [0] * (len(seq) + 1)


def test_bounces_restart_the_count():
    seq = [1, 1, 1, 0, 1, 1, 1, 1, 0, 0]
    assert run(4, seq) == model(4, seq)


def test_release_is_debounced_too():
    seq = [1] * 6 + [0, 1, 0, 0, 0, 0, 0]
    assert run(3, seq) == model(3, seq)
