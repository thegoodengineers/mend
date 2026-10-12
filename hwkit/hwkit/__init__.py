"""hwkit: more synchronous digital designs in Amaranth HDL, built on hwlib.

hwlib (in hardware/) is the benchmark sandbox for the hardware transfer test: its designs and
testbenches are pinned, so they stay as they are. hwkit adds the parts a real board needs around
them (a UART receiver, an SPI master, an LFSR, an edge detector, a seven-segment decoder) and one
composed design that wires hwlib and hwkit blocks together (a UART echo through a FIFO).

Same conventions as hwlib: one clock domain (`sync`), ports listed in each docstring, every design
checked cycle by cycle against a plain-Python model (hwkit/tests).
"""
