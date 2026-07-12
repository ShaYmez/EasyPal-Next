"""Tests for honest HamDRM sync LED decoding."""

from easypal_next.modem.hamdrm_backend import (
    _STATE_FAC,
    _STATE_FRAME,
    _STATE_IO,
    _STATE_MSC,
    _STATE_TIME,
    led_is_green,
)


def test_led_green_only_for_zero():
    assert led_is_green(0) is True
    assert led_is_green(1) is False
    assert led_is_green(2) is False
    assert led_is_green(-1) is False


def test_getstate_indices_match_messid():
    # Must not use 0–4 sequential UI order — indices are MessIDs.
    assert _STATE_FAC == 1
    assert _STATE_MSC == 2
    assert _STATE_FRAME == 3
    assert _STATE_TIME == 4
    assert _STATE_IO == 5


def test_idle_vector_all_unset_is_dark():
    states = [-1] * 8
    assert not any(
        led_is_green(states[i])
        for i in (_STATE_IO, _STATE_TIME, _STATE_FRAME, _STATE_FAC, _STATE_MSC)
    )


def test_fac_lock_only_fac_green():
    states = [-1] * 8
    states[_STATE_FAC] = 0
    states[_STATE_IO] = 2
    assert led_is_green(states[_STATE_FAC]) is True
    assert led_is_green(states[_STATE_MSC]) is False
    assert led_is_green(states[_STATE_IO]) is False
