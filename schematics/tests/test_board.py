"""Bring-up checks for the sensor board, as an engineer runs them in simulation before ordering PCBs."""

import pytest

from circuits.spice import load

MCU_ABS_MAX = 3.6     # volts on any MCU pin
GPIO_MAX = 20e-3      # amps a GPIO pin may source


@pytest.fixture(scope="module")
def op():
    return load("board").dc()


def test_rail_is_3v3(op):
    assert op.v("v33") == pytest.approx(3.3, rel=0.02)


def test_power_led_on_at_about_1ma(op):
    assert 0.8e-3 < op.i("DPWR") < 2e-3


def test_sensor_reads_half_rail_at_25c(op):
    assert op.v("sense") == pytest.approx(op.v("v33") / 2, rel=0.02)


def test_sensor_voltage_rises_when_warm():
    warm = load("board").with_value("RNTC", "3.3k").dc()  # NTC at about 60 C
    assert 2.3 < warm.v("sense") < 2.6


def test_adc_sees_the_buffered_sensor_voltage(op):
    assert op.v("adc") == pytest.approx(op.v("sense"), rel=0.001)
    assert 0 <= op.v("adc") <= op.v("v33")


def test_anti_aliasing_cutoff_is_1khz():
    board = load("board")
    assert board.ac(1000).gain_db("adc", "ain") == pytest.approx(-3.0, abs=0.3)
    assert board.ac(100).gain_db("adc", "ain") > -0.1
    assert board.ac(10000).gain_db("adc", "ain") < -19


def test_board_runs_when_reset_released(op):
    assert op.v("rst") > 0.9 * op.v("v33")


def test_reset_button_pulls_reset_low():
    assert load("board").with_value("RBTN", "1m").dc().v("rst") < 0.3


def test_status_led_current_is_safe_for_the_gpio(op):
    assert 4e-3 < op.i("DLED") < 10e-3
    assert op.i("DLED") <= GPIO_MAX


def test_i2c_lines_idle_high_within_mcu_limits(op):
    for line in ("sda", "scl"):
        assert 0.9 * op.v("v33") < op.v(line) <= MCU_ABS_MAX, line


def test_regulator_load_is_modest(op):
    assert 0 < op.i("EREG") < 50e-3
