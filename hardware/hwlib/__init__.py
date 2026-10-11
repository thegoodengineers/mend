"""hwlib: small synchronous digital designs in Amaranth HDL, each checked by a cycle-accurate simulation.

Every design is an Amaranth Elaboratable with one clock domain (`sync`); outputs listed in each
docstring. `python -c "from amaranth.back import verilog; ..."` turns any of them into Verilog.
"""
