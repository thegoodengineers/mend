from simhelp import settle, simulate

from hwkit.sevenseg import GLYPHS, SevenSeg
from hwkit.sync import EdgeDetect

# Which segments (a-g) each hex digit lights, written out by hand as an independent reference.
LIT = ["abcdef", "bc", "abdeg", "abcdg", "bcfg", "acdfg", "acdefg", "abc",
       "abcdefg", "abcdfg", "abcefg", "cdefg", "adef", "bcdeg", "adefg", "aefg"]


def segs(letters):
    return sum(1 << "abcdefg".index(ch) for ch in letters)


def decode(active_low=False, blank=0):
    dut = SevenSeg(active_low)
    out = []

    async def bench(ctx):
        ctx.set(dut.blank, blank)
        for d in range(16):
            ctx.set(dut.digit, d)
            await settle(ctx)
            out.append(ctx.get(dut.segments))

    simulate(dut, bench, clock=False)
    return out


def test_glyph_table_matches_hand_reference():
    assert GLYPHS == [segs(s) for s in LIT]


def test_decodes_every_hex_digit():
    assert decode() == [segs(s) for s in LIT]


def test_active_low_inverts():
    assert decode(active_low=True) == [~segs(s) & 0x7F for s in LIT]


def test_blank_turns_everything_off():
    assert decode(blank=1) == [0] * 16
    assert decode(active_low=True, blank=1) == [0x7F] * 16


def edges(raw):
    dut = EdgeDetect()
    seen = []

    async def bench(ctx):
        for level in raw:
            ctx.set(dut.raw, level)
            await ctx.tick()
            seen.append((ctx.get(dut.level), ctx.get(dut.rise), ctx.get(dut.fall)))

    simulate(dut, bench)
    return seen


def test_level_is_raw_two_cycles_late():
    raw = [0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0]
    level = [s[0] for s in edges(raw)]
    assert level[1:] == raw[:-1][:len(level) - 1]  # registered twice: visible one tick after the 2nd edge


def test_one_pulse_per_edge():
    raw = [0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0]
    seen = edges(raw)
    rises = [i for i, s in enumerate(seen) if s[1]]
    falls = [i for i, s in enumerate(seen) if s[2]]
    assert len(rises) == 2 and len(falls) == 2
    for i in rises:
        assert seen[i][0] == 1 and seen[i - 1][0] == 0
    for i in falls:
        assert seen[i][0] == 0 and seen[i - 1][0] == 1


def test_steady_input_never_pulses():
    assert all(not r and not f for _, r, f in edges([1] * 10)[3:])
