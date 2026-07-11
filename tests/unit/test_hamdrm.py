"""Unit tests for HamDRM path resolution and SyncState defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from easypal_next.modem.hamdrm_api import (
    EASYPAL_PROGRAM_FILES,
    IMAGE_FILE_MACHINE_AMD64,
    IMAGE_FILE_MACHINE_I386,
    HamDrmUnavailable,
    dll_matches_python,
    load_hamdrm,
    pe_machine,
    python_is_64bit,
    resolve_hamdrm_dll,
)
from easypal_next.modem.transfer_backend import SyncState

RUN_DLL = EASYPAL_PROGRAM_FILES / "run.dll"
BUILT_X64 = (
    Path(__file__).resolve().parents[2]
    / "native"
    / "hamdrm-dll"
    / "build-x64"
    / "bin"
    / "hamdrm.dll"
)


def test_sync_state_defaults() -> None:
    state = SyncState()
    assert state.io is False
    assert state.time is False
    assert state.frame is False
    assert state.fac is False
    assert state.msc is False
    assert state.snr_db is None
    assert state.level is None
    assert state.dc_freq is None
    assert state.callsign == ""
    assert state.mode == ""


@pytest.mark.skipif(not RUN_DLL.is_file(), reason="EasyPal run.dll not installed")
def test_run_dll_is_32bit_and_skipped_on_64bit_python() -> None:
    machine = pe_machine(RUN_DLL)
    assert machine == IMAGE_FILE_MACHINE_I386
    if not python_is_64bit():
        pytest.skip("Test expects 64-bit Python vs 32-bit run.dll")
    assert dll_matches_python(RUN_DLL) is False
    resolved = resolve_hamdrm_dll(None)
    # Must not pick the 32-bit EasyPal run.dll under 64-bit Python.
    if resolved is not None:
        assert pe_machine(resolved) != IMAGE_FILE_MACHINE_I386
        assert dll_matches_python(resolved)


@pytest.mark.skipif(not BUILT_X64.is_file(), reason="x64 hamdrm.dll not built yet")
def test_resolve_prefers_matching_x64_build() -> None:
    if not python_is_64bit():
        pytest.skip("Built DLL is x64")
    resolved = resolve_hamdrm_dll(None)
    assert resolved is not None
    assert pe_machine(resolved) == IMAGE_FILE_MACHINE_AMD64
    assert dll_matches_python(resolved)


@pytest.mark.skipif(not RUN_DLL.is_file(), reason="EasyPal run.dll not installed")
def test_hamdrm_load_reports_bitness_mismatch() -> None:
    machine = pe_machine(RUN_DLL)
    assert machine == IMAGE_FILE_MACHINE_I386
    if not python_is_64bit():
        pytest.skip("Test expects 64-bit Python vs 32-bit run.dll")
    with pytest.raises(HamDrmUnavailable) as exc_info:
        load_hamdrm(RUN_DLL)
    message = str(exc_info.value).lower()
    assert "bitness" in message or "193" in message or "32-bit" in message
    assert "64-bit" in message
