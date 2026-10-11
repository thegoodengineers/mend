# hwlib: the hardware transfer test

Eight small synchronous digital designs in [Amaranth HDL](https://amaranth-lang.org) (BSD-2-clause,
`amaranth==0.5.4`): a counter, Gray code converters, an 8-bit ALU, a FIFO, a UART transmitter, a PWM
generator, a debouncer, and a CRC-8 unit. Each is checked cycle by cycle against a plain-Python
reference model by an Amaranth simulation testbench (`tests/`, 26 tests). Any of them can be emitted
as Verilog (`python scripts/hw_demo.py verilog uart`, after `pip install amaranth-yosys`).

`tasks/hardware.json` plants 9 bugs here, each with a symptom-only bug report. The supervisor never
sees them. They test whether a worker repaired on Python business-logic bugs carries over to a
domain it never saw:

    python -m mend.suite --hardware

Try it by hand (no API key needed):

    python -m pytest -q hardware               # 26 testbenches pass on the correct designs
    python scripts/hw_demo.py bug HW06         # plant one bug and watch its testbench fail
    python scripts/hw_demo.py bugs             # all 9 bugs: each is caught
