from simhelp import simulate

from hwlib.pwm import PWM


def waveform(period, duty, cycles):
    dut = PWM(period)
    out = []

    async def bench(ctx):
        ctx.set(dut.duty, duty)
        for _ in range(cycles):
            out.append(ctx.get(dut.out))
            await ctx.tick()

    simulate(dut, bench)
    return out


def test_duty_sets_high_cycles_per_period():
    for duty in range(0, 9):
        out = waveform(8, duty, 32)
        assert sum(out) == 4 * duty, duty
        assert out[:8] == [1] * duty + [0] * (8 - duty), duty


def test_zero_duty_is_always_low():
    assert waveform(10, 0, 30) == [0] * 30


def test_full_duty_is_always_high():
    assert waveform(10, 10, 30) == [1] * 30
