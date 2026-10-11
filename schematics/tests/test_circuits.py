"""Each circuit against its spec, as a board designer would check it in simulation before ordering PCBs."""

import pytest

from circuits.spice import load


def test_divider_gives_3v3_from_5v():
    assert load("divider").dc().v("out") == pytest.approx(3.3, rel=0.02)


def test_led_current_is_10_ma():
    assert load("led").dc().i("D1") == pytest.approx(10e-3, rel=0.05)


def test_led_stays_under_its_rating():
    assert 0 < load("led").dc().i("D1") <= 20e-3


def test_lowpass_cutoff_is_1_khz():
    c = load("lowpass")
    assert c.ac(1000).gain_db("out", "in") == pytest.approx(-3.0, abs=0.3)
    assert c.ac(100).gain_db("out", "in") > -0.1   # passband
    assert c.ac(10000).gain_db("out", "in") < -19  # one decade up: about -20 dB


def test_noninverting_gain_is_11():
    assert load("noninv").dc().v("out") == pytest.approx(1.1, rel=0.01)


def test_button_released_reads_high():
    assert load("pullup").dc().v("pin") == pytest.approx(3.3, rel=0.01)


def test_button_pressed_reads_low():
    assert load("pullup").with_value("RSW", "1m").dc().v("pin") < 0.1


def test_highpass_cutoff_is_1_khz():
    c = load("highpass")
    assert c.ac(1000).gain_db("out", "in") == pytest.approx(-3.0, abs=0.3)
    assert c.ac(10000).gain_db("out", "in") > -0.1  # passband
    assert c.ac(100).gain_db("out", "in") < -19     # one decade down: about -20 dB


def test_inverting_gain_is_minus_4_7():
    assert load("inverting").dc().v("out") == pytest.approx(-0.94, rel=0.01)
