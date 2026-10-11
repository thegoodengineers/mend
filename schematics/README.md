# circuits: the schematic transfer test

Seven board-level circuits written as netlists, the text form of a schematic that KiCad exports and
SPICE simulates: a voltage divider, an LED driver, RC low-pass and high-pass filters, non-inverting
and inverting op-amp amplifiers, and a push-button pull-up. [`circuits/spice.py`](circuits/spice.py)
is a small circuit simulator (Modified Nodal Analysis, DC operating point and AC response). It is
checked against hand calculations in `tests/test_simulator.py`, and each circuit is checked against
its spec in `tests/test_circuits.py`, for example 3.3 V out, LED at 10 mA, or a 1 kHz cutoff.

`tasks/schematics.json` plants 8 bugs of the kind made at board bring-up: a wrong resistor value or
unit, a reversed LED, a pull-down where a pull-up belongs, R and C swapped, a resistor wired to the
wrong net. The supervisor never sees them.

    python -m pytest -q schematics            # 15 tests pass on the correct circuits
    python -m mend.suite --schematics         # run the worker on the 8 planted bugs (uses the API)
