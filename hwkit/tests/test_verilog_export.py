import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.skipif(importlib.util.find_spec("amaranth_yosys") is None,
                                reason="needs amaranth-yosys (pip install -e .[verilog])")


def designs():
    from hw_demo import DESIGNS
    return list(DESIGNS)


@pytest.mark.parametrize("name", designs())
def test_committed_verilog_matches_the_design(name):
    """hwkit/verilog is generated; if a design changes, regenerate with `hw_demo.py verilog all`."""
    from hw_demo import to_verilog
    committed = (ROOT / "hwkit" / "verilog" / f"{name}.v").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == to_verilog(name) + "\n"


def test_benchmark_verilog_is_unchanged():
    """The three Verilog files inside the pinned benchmark sandbox match their generator too."""
    for name in ("counter", "pwm", "uart"):
        sandbox = (ROOT / "hardware" / "verilog" / f"{name}.v").read_text(encoding="utf-8").replace("\r\n", "\n")
        assert sandbox == (ROOT / "hwkit" / "verilog" / f"{name}.v").read_text(encoding="utf-8").replace("\r\n", "\n")
