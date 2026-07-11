"""ctypes loader and bindings for HamDRM-compatible DLLs (hamdrm.dll / run.dll).

Original EasyPal ships a 32-bit ``run.dll`` with the same exports as ``hamdrm.h``.
64-bit Python cannot LoadLibrary a 32-bit DLL (WinError 193); bindings are ready
for a matching 64-bit DLL when one is available.
"""

from __future__ import annotations

import ctypes
import os
import struct
import sys
from ctypes import CDLL, POINTER, c_bool, c_char, c_char_p, c_float, c_int
from pathlib import Path

from easypal_next.app.paths import app_root, package_root, user_data_dir

# Constants from hamdrm.h
MODE_A = 0
MODE_B = 1
MODE_E = 2

SPECOCC_23 = 0
SPECOCC_25 = 1

MSCPROT_NORM = 0
MSCPROT_LOW = 1

QAM_4 = 0
QAM_16 = 1
QAM_64 = 2

INTERLEAVE_SHORT = 0
INTERLEAVE_LONG = 1

SPECTRUM_BINS = 500
CALLSIGN_MAX = 9
PATH_MAX_CHARS = 200

IMAGE_FILE_MACHINE_I386 = 0x014C
IMAGE_FILE_MACHINE_AMD64 = 0x8664

EASYPAL_PROGRAM_FILES = Path(r"C:\Program Files\EasyPal")
EASYPAL_PROGRAM_FILES_X86 = Path(r"C:\Program Files (x86)\EasyPal")


class HamDrmUnavailable(RuntimeError):
    """Raised when the HamDRM DLL is missing or cannot be loaded (e.g. bitness)."""


def pe_machine(path: Path) -> int | None:
    """Return PE Machine field, or None if not a valid PE."""
    try:
        with path.open("rb") as fh:
            if fh.read(2) != b"MZ":
                return None
            fh.seek(0x3C)
            pe_off = struct.unpack("<I", fh.read(4))[0]
            fh.seek(pe_off)
            if fh.read(4) != b"PE\0\0":
                return None
            return struct.unpack("<H", fh.read(2))[0]
    except OSError:
        return None


def pe_bitness_label(machine: int | None) -> str:
    if machine == IMAGE_FILE_MACHINE_I386:
        return "32-bit"
    if machine == IMAGE_FILE_MACHINE_AMD64:
        return "64-bit"
    if machine is None:
        return "unknown"
    return f"unknown(0x{machine:04x})"


def python_is_64bit() -> bool:
    return struct.calcsize("P") == 8


def candidate_hamdrm_paths(configured_path: str | None = None) -> list[Path]:
    """Ordered search list for HamDRM-compatible DLLs."""
    candidates: list[Path] = []

    def _add(path: Path) -> None:
        resolved = path.expanduser()
        if resolved not in candidates:
            candidates.append(resolved)

    if configured_path:
        _add(Path(configured_path))

    _add(user_data_dir() / "hamdrm.dll")
    _add(EASYPAL_PROGRAM_FILES / "run.dll")
    _add(EASYPAL_PROGRAM_FILES / "hamdrm.dll")
    _add(EASYPAL_PROGRAM_FILES_X86 / "run.dll")
    _add(EASYPAL_PROGRAM_FILES_X86 / "hamdrm.dll")

    # Next to executable / packaging redist
    root = app_root()
    pkg = package_root()
    for base in (root, pkg, root / "_internal", pkg / "modem"):
        _add(base / "hamdrm.dll")
        _add(base / "run.dll")
    _add(root / "packaging" / "windows" / "redist" / "hamdrm.dll")
    _add(root / "packaging" / "windows" / "redist" / "run.dll")

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        _add(exe_dir / "hamdrm.dll")
        _add(exe_dir / "run.dll")

    return candidates


def resolve_hamdrm_dll(configured_path: str | None = None) -> Path | None:
    """Return the first existing candidate path, or None."""
    for path in candidate_hamdrm_paths(configured_path):
        if path.is_file():
            return path
    return None


def _bitness_mismatch_message(path: Path, machine: int | None) -> str:
    dll_bits = pe_bitness_label(machine)
    py_bits = "64-bit" if python_is_64bit() else "32-bit"
    return (
        f"HamDRM DLL bitness mismatch: {path} is {dll_bits} but Python is {py_bits}. "
        f"In-process LoadLibrary fails with WinError 193. "
        f"Install a matching {py_bits} hamdrm.dll (or run EasyPal-Next under {dll_bits} Python), "
        f"or keep engine=freedv until a {py_bits} HamDRM build is available."
    )


def load_hamdrm(path: Path | str) -> CDLL:
    """Load a HamDRM-compatible DLL and bind exports.

    Uses CDLL (cdecl) to match ``hamdrm.h`` / ``run.dll``. Raises
    :class:`HamDrmUnavailable` when the file is missing or the wrong bitness.
    """
    dll_path = Path(path).expanduser().resolve()
    if not dll_path.is_file():
        raise HamDrmUnavailable(
            f"HamDRM DLL not found: {dll_path}. "
            "Install EasyPal (run.dll) or place a matching hamdrm.dll under "
            f"%APPDATA%/EasyPal-Next/ or {EASYPAL_PROGRAM_FILES}."
        )

    machine = pe_machine(dll_path)
    dll_64 = machine == IMAGE_FILE_MACHINE_AMD64
    dll_32 = machine == IMAGE_FILE_MACHINE_I386
    if machine is not None and ((python_is_64bit() and dll_32) or (not python_is_64bit() and dll_64)):
        raise HamDrmUnavailable(_bitness_mismatch_message(dll_path, machine))

    dll_dir = str(dll_path.parent)
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(dll_dir)
        except OSError:
            pass

    try:
        # cdecl exports — CDLL on both 32/64; WinDLL would be wrong on 32-bit stdcall.
        lib = CDLL(str(dll_path))
    except OSError as exc:
        winerr = getattr(exc, "winerror", None)
        if winerr == 193 or "193" in str(exc):
            raise HamDrmUnavailable(_bitness_mismatch_message(dll_path, machine)) from exc
        raise HamDrmUnavailable(f"Failed to load HamDRM DLL {dll_path}: {exc}") from exc

    bind_hamdrm(lib)
    return lib


def bind_hamdrm(lib: CDLL) -> CDLL:
    """Attach argtypes/restype for major hamdrm.h / run.dll exports."""
    lib.getFatalErr.argtypes = []
    lib.getFatalErr.restype = c_int

    lib.SetRXFileSavePath.argtypes = [c_char_p]
    lib.SetRXFileSavePath.restype = None
    lib.SetRXCorruptSavePath.argtypes = [c_char_p]
    lib.SetRXCorruptSavePath.restype = None
    lib.SetBSRPath.argtypes = [c_char_p]
    lib.SetBSRPath.restype = None

    lib.SetParams.argtypes = [c_int, c_int, c_int, c_int, c_int]
    lib.SetParams.restype = None
    lib.SetCall.argtypes = [c_char_p]
    lib.SetCall.restype = None
    lib.SetDCFreq.argtypes = [c_int]
    lib.SetDCFreq.restype = None
    lib.SetStartDelay.argtypes = [c_int]
    lib.SetStartDelay.restype = None

    lib.GetParams.argtypes = [
        POINTER(c_char),
        POINTER(c_char),
        POINTER(c_char),
        POINTER(c_char),
        POINTER(c_char),
    ]
    lib.GetParams.restype = c_bool
    lib.GetCall.argtypes = [c_char_p]
    lib.GetCall.restype = c_bool

    lib.GetAudNumDevIn.argtypes = []
    lib.GetAudNumDevIn.restype = c_int
    lib.GetAudDeviceNameIn.argtypes = [c_int]
    lib.GetAudDeviceNameIn.restype = c_char_p
    lib.SetAudDeviceIn.argtypes = [c_int]
    lib.SetAudDeviceIn.restype = None
    lib.GetAudNumDevOut.argtypes = []
    lib.GetAudNumDevOut.restype = c_int
    lib.GetAudDeviceNameOut.argtypes = [c_int]
    lib.GetAudDeviceNameOut.restype = c_char_p
    lib.SetAudDeviceOut.argtypes = [c_int]
    lib.SetAudDeviceOut.restype = None

    lib.SetCommDevice.argtypes = [c_int]
    lib.SetCommDevice.restype = None
    lib.SetPTT.argtypes = [c_int]
    lib.SetPTT.restype = None

    lib.SetFileTX.argtypes = [c_char_p, c_char_p, c_int]
    lib.SetFileTX.restype = c_bool
    lib.GetFileRX.argtypes = [c_char_p]
    lib.GetFileRX.restype = c_bool
    lib.GetCorruptFileRX.argtypes = [c_char_p]
    lib.GetCorruptFileRX.restype = c_bool
    lib.GetPercentTX.argtypes = [POINTER(c_int), POINTER(c_int)]
    lib.GetPercentTX.restype = c_bool
    lib.GetSegPosTX.argtypes = [POINTER(c_int), POINTER(c_int)]
    lib.GetSegPosTX.restype = None
    lib.GetActSegm.argtypes = [c_char_p]
    lib.GetActSegm.restype = c_bool
    lib.GetLastTID.argtypes = []
    lib.GetLastTID.restype = c_int

    lib.GetBSR.argtypes = [POINTER(c_int), c_char_p]
    lib.GetBSR.restype = c_bool
    lib.SendBSR.argtypes = [c_int, c_int]
    lib.SendBSR.restype = c_bool
    lib.readthebsrfile.argtypes = [c_char_p, POINTER(c_int)]
    lib.readthebsrfile.restype = c_bool
    lib.writebsrselsegments.argtypes = [c_int]
    lib.writebsrselsegments.restype = None

    lib.StartThreadRX.argtypes = [c_int]
    lib.StartThreadRX.restype = None
    lib.StartThreadTX.argtypes = [c_int]
    lib.StartThreadTX.restype = None
    lib.StopThreads.argtypes = []
    lib.StopThreads.restype = None

    lib.ControlTX.argtypes = [c_bool]
    lib.ControlTX.restype = None
    lib.ControlRX.argtypes = [c_bool]
    lib.ControlRX.restype = None
    lib.ResetRX.argtypes = []
    lib.ResetRX.restype = None

    lib.GetSpectrum.argtypes = [POINTER(c_float)]
    lib.GetSpectrum.restype = c_int
    lib.GetSPSD.argtypes = [POINTER(c_float)]
    lib.GetSPSD.restype = c_int
    lib.GetTF.argtypes = [POINTER(c_float), POINTER(c_float)]
    lib.GetTF.restype = c_int
    lib.GetIR.argtypes = [
        POINTER(c_float),
        POINTER(c_float),
        POINTER(c_float),
        POINTER(c_float),
        POINTER(c_float),
        POINTER(c_float),
        POINTER(c_float),
    ]
    lib.GetIR.restype = c_int
    lib.GetFAC.argtypes = [POINTER(c_float), POINTER(c_float)]
    lib.GetFAC.restype = c_int
    lib.GetMSC.argtypes = [POINTER(c_float), POINTER(c_float)]
    lib.GetMSC.restype = c_int

    lib.GetSNR.argtypes = []
    lib.GetSNR.restype = c_int
    lib.GetLevel.argtypes = []
    lib.GetLevel.restype = c_int
    lib.GetDCFreq.argtypes = []
    lib.GetDCFreq.restype = c_int
    lib.GetState.argtypes = [POINTER(c_int)]
    lib.GetState.restype = c_int
    lib.GetData.argtypes = [POINTER(c_int), POINTER(c_int), POINTER(c_int)]
    lib.GetData.restype = None

    # run.dll extension (not in all hamdrm.h revisions)
    if hasattr(lib, "SetHeaderRepRate"):
        lib.SetHeaderRepRate.argtypes = [c_int]
        lib.SetHeaderRepRate.restype = None

    return lib


def mode_constant(mode: str) -> int:
    return {"A": MODE_A, "B": MODE_B, "E": MODE_E}[mode.upper()]


def specocc_constant(specocc: str) -> int:
    return {"2.3": SPECOCC_23, "2.5": SPECOCC_25}[specocc]


def mscprot_constant(mscprot: str) -> int:
    return {"normal": MSCPROT_NORM, "low": MSCPROT_LOW}[mscprot.lower()]


def qam_constant(qam: int) -> int:
    return {4: QAM_4, 16: QAM_16, 64: QAM_64}[qam]


def interleave_constant(interleave: str) -> int:
    return {"short": INTERLEAVE_SHORT, "long": INTERLEAVE_LONG}[interleave.lower()]


def encode_c_path(path: Path | str) -> bytes:
    text = str(path)
    if len(text) >= PATH_MAX_CHARS:
        raise ValueError(f"Path exceeds HamDRM {PATH_MAX_CHARS}-char limit: {text}")
    return text.encode("mbcs", errors="replace")


def encode_callsign(callsign: str) -> bytes:
    trimmed = (callsign or "N0CALL")[:CALLSIGN_MAX]
    return trimmed.encode("ascii", errors="replace")
