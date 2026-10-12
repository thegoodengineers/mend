import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# hwkit builds on hwlib and reuses its simulation helper; neither is copied, so the pinned
# benchmark sandbox in hardware/ stays byte-for-byte the same.
for path in (HERE, HERE.parent / "hardware", HERE.parent / "hardware" / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pytest_configure(config):
    # A constructor that rejects its parameters still leaves a half-built Elaboratable behind.
    config.addinivalue_line("filterwarnings", "ignore::amaranth.hdl._ir.UnusedElaboratable")
