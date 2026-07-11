"""Unit tests for HamDRM path resolution and SyncState defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from easypal_next.modem.hamdrm_api import (
    EASYPAL_PROGRAM_FILES,
    HamDrmUnavailable,
    load_hamdrm,
    pe_machine,
    python_is_64bit,
    resolve_hamdrm_dll,
)
from easypal_next.modem.transfer_backend import SyncState

RUN_DLL = EASYPAL_PROGRAM_FILES / "run.dll"


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
def test_hamdrm_resolve_finds_program_files_run_dll() -> None:
    resolved = resolve_hamdrm_dll(None)
    assert resolved is not None
    assert resolved.is_file()
    # Prefer EasyPal run.dll when present (hamdrm.dll is usually absent).
    assert resolved.name.lower() in {"run.dll", "hamdrm.dll"}
    assert "easypal" in str(resolved).lower() or resolved == RUN_DLL


@pytest.mark.skipif(not RUN_DLL.is_file(), reason="EasyPal run.dll not installed")
def test_hamdrm_load_reports_bitness_mismatch() -> None:
    machine = pe_machine(RUN_DLL)
    assert machine == 0x014C  # 32-bit EasyPal run.dll
    if not python_is_64bit():
        pytest.skip("Test expects 64-bit Python vs 32-bit run.dll")
    with pytest.raises(HamDrmUnavailable) as exc_info:
        load_hamdrm(RUN_DLL)
    message = str(exc_info.value).lower()
    assert "bitness" in message or "193" in message or "32-bit" in message
    assert "64-bit" in message
