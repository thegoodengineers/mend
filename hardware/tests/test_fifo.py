from collections import deque

from simhelp import simulate

from hwlib.fifo import SyncFIFO


def run_fifo(depth, ops):
    """ops: list of (w_en, w_data, r_en). Returns per-cycle (level, empty, full, r_data) before each edge."""
    dut = SyncFIFO(8, depth)
    seen = []

    async def bench(ctx):
        for w_en, w_data, r_en in ops:
            ctx.set(dut.w_en, w_en)
            ctx.set(dut.w_data, w_data)
            ctx.set(dut.r_en, r_en)
            seen.append((ctx.get(dut.level), ctx.get(dut.empty), ctx.get(dut.full), ctx.get(dut.r_data)))
            await ctx.tick()

    simulate(dut, bench)
    return seen


def model(depth, ops):
    q, out = deque(), []
    for w_en, w_data, r_en in ops:
        out.append((len(q), int(not q), int(len(q) == depth), q[0] if q else None))
        do_w, do_r = w_en and len(q) < depth, r_en and q
        if do_r:
            q.popleft()
        if do_w:
            q.append(w_data)
    return out


def compare(depth, ops):
    for cycle, (got, want) in enumerate(zip(run_fifo(depth, ops), model(depth, ops))):
        assert got[:3] == want[:3], (cycle, got, want)
        if want[3] is not None:
            assert got[3] == want[3], (cycle, got, want)


def test_fill_to_full_then_drain_in_order():
    ops = [(1, 10 + i, 0) for i in range(6)] + [(0, 0, 1)] * 6
    compare(4, ops)


def test_full_only_when_every_slot_is_used():
    seen = run_fifo(4, [(1, i, 0) for i in range(5)])
    assert [full for _, _, full, _ in seen] == [0, 0, 0, 0, 1]


def test_simultaneous_read_and_write_keeps_level():
    ops = [(1, 1, 0), (1, 2, 0), (1, 3, 1), (1, 4, 1), (1, 5, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)]
    compare(4, ops)


def test_pointers_wrap_around_many_times():
    ops = [(1, i & 0xFF, int(i % 3 != 0)) for i in range(40)] + [(0, 0, 1)] * 5
    compare(4, ops)
