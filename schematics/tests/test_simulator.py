"""The simulator itself, checked against hand calculations (so circuit tests can trust it)."""

import math

import pytest

from circuits.spice import Circuit, value


def test_suffixes():
    assert value("10k") == 10e3 and value("100n") == pytest.approx(100e-9)
    assert value("1meg") == 1e6 and value("4.7u") == pytest.approx(4.7e-6) and value("2m") == 2e-3


def test_series_resistors_split_the_voltage():
    op = Circuit("V1 a 0 DC 9\nR1 a b 1k\nR2 b 0 2k").dc()
    assert op.v("b") == pytest.approx(6.0)
    assert op.i("V1") == pytest.approx(3e-3)


def test_diode_conducts_forward_and_blocks_reverse():
    fwd = Circuit("V1 a 0 DC 5\nR1 a k 1k\nD1 k 0 VF=0.7").dc()
    assert fwd.i("D1") == pytest.approx(4.3e-3)
    rev = Circuit("V1 a 0 DC 5\nR1 a k 1k\nD1 0 k VF=0.7").dc()
    assert rev.i("D1") == 0 and rev.v("k") == pytest.approx(5.0)


def test_rc_corner_is_minus_3_db():
    fc = 1 / (2 * math.pi * 1e3 * 1e-6)
    res = Circuit("V1 in 0 AC 1\nR1 in out 1k\nC1 out 0 1u").ac(fc)
    assert res.gain_db("out", "in") == pytest.approx(-3.0103, abs=0.01)


def test_capacitor_is_open_at_dc():
    assert Circuit("V1 in 0 DC 5\nR1 in out 1k\nC1 out 0 1u").dc().v("out") == pytest.approx(5.0)


def test_floating_node_is_reported():
    with pytest.raises(ValueError):
        Circuit("V1 a 0 DC 5\nR1 b c 1k").dc()
