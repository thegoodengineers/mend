"""Run an Amaranth testbench: `simulate(dut, bench)` where bench is `async def bench(ctx)`."""

from amaranth.sim import Simulator


def simulate(dut, bench, clock: bool = True) -> None:
    sim = Simulator(dut)
    if clock:
        sim.add_clock(1e-6)
    sim.add_testbench(bench)
    sim.run()


async def settle(ctx) -> None:
    """Let combinational logic settle after setting inputs (for designs with no clock)."""
    await ctx.delay(1e-9)
