import itertools

from simhelp import settle, simulate

from hwlib.alu import ADD, ALU, AND, OR, SUB, XOR

VALUES = [0, 1, 2, 7, 15, 64, 127, 128, 200, 254, 255]


def reference(op, a, b):
    if op == ADD:
        return (a + b) & 0xFF, int(a + b > 0xFF)
    if op == SUB:
        return (a - b) & 0xFF, int(a < b)
    return {AND: a & b, OR: a | b, XOR: a ^ b}[op], 0


def run_alu(cases):
    dut = ALU()
    got = []

    async def bench(ctx):
        for op, a, b in cases:
            ctx.set(dut.op, op)
            ctx.set(dut.a, a)
            ctx.set(dut.b, b)
            await settle(ctx)
            got.append((ctx.get(dut.result), ctx.get(dut.carry), ctx.get(dut.zero)))

    simulate(dut, bench, clock=False)
    return got


def test_every_op_matches_the_reference_model():
    cases = [(op, a, b) for op in (ADD, SUB, AND, OR, XOR) for a, b in itertools.product(VALUES, VALUES)]
    for (op, a, b), (result, carry, zero) in zip(cases, run_alu(cases)):
        want, want_carry = reference(op, a, b)
        assert (result, carry, zero) == (want, want_carry, int(want == 0)), (op, a, b)


def test_sub_is_a_minus_b():
    [(result, borrow, _)] = run_alu([(SUB, 10, 3)])
    assert (result, borrow) == (7, 0)
