import pytest
from simhelp import simulate

from hwkit.lfsr import LFSR, TAPS, lfsr_step


def model_period(width, taps, seed=1):
    state, n = lfsr_step(seed, width, taps), 1
    while state != seed:
        state, n = lfsr_step(state, width, taps), n + 1
        assert n < 1 << width, "not a cycle through the seed"
    return n


@pytest.mark.parametrize("width", [w for w in TAPS if w <= 20])
def test_default_taps_are_maximal_length(width):
    assert model_period(width, TAPS[width]) == (1 << width) - 1


def run(dut, cycles, en=lambda i: 1):
    seen = []

    async def bench(ctx):
        for i in range(cycles):
            ctx.set(dut.en, en(i))
            seen.append((ctx.get(dut.state), ctx.get(dut.out)))
            await ctx.tick()

    simulate(dut, bench)
    return seen


@pytest.mark.parametrize("width,seed", [(4, 1), (8, 0xA5), (16, 0xACE1)])
def test_hardware_matches_model(width, seed):
    dut = LFSR(width, seed=seed)
    state = seed
    for got_state, got_out in run(dut, 300):
        assert got_state == state
        assert got_out == state >> (width - 1)
        state = lfsr_step(state, width, TAPS[width])


def test_full_period_in_hardware():
    dut = LFSR(7)
    states = [s for s, _ in run(dut, 128)]
    assert len(set(states[:127])) == 127 and 0 not in states
    assert states[127] == states[0]


def test_holds_when_disabled():
    dut = LFSR(8, seed=0x5A)
    states = [s for s, _ in run(dut, 10, en=lambda i: i % 2)]
    assert states[0] == states[1] == 0x5A
    assert states[2] == states[3] == lfsr_step(0x5A, 8, TAPS[8])


def test_custom_taps():
    dut = LFSR(5, seed=3, taps=(5, 2))  # also maximal for width 5
    assert model_period(5, (5, 2), seed=3) == 31
    state = 3
    for got, _ in run(dut, 40):
        assert got == state
        state = lfsr_step(state, 5, (5, 2))


@pytest.mark.parametrize("kwargs", [dict(width=8, seed=0), dict(width=8, seed=256),
                                    dict(width=21), dict(width=8, taps=(9, 1)), dict(width=8, taps=())])
def test_rejects_bad_parameters(kwargs):
    with pytest.raises(ValueError):
        LFSR(**kwargs)
