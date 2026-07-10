#!/usr/bin/env python3
"""Verify libcodec2.dll loads and DATAC3 modem opens."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from easypal_next.app.paths import resolve_libcodec2  # noqa: E402
from easypal_next.modem.ctypes_backend import CtypesFreeDvModem  # noqa: E402


def main() -> int:
    lib_path = resolve_libcodec2(None)
    if lib_path is None:
        redist = ROOT / "packaging" / "windows" / "redist" / "libcodec2.dll"
        print("ERROR: libcodec2.dll not found.")
        print(f"  Place DLL at: {redist}")
        print("  See docs/codec2-windows-setup.md")
        return 1

    print(f"Loading: {lib_path}")
    modem = CtypesFreeDvModem(lib_path)
    try:
        modem.open("DATAC3", sample_rate=8000)
        print("  Mode: DATAC3")
        print(f"  Modem sample rate: {modem.modem_sample_rate} Hz")
        print(f"  Frame payload size: {modem.frame_payload_size} bytes")
        print(f"  TX samples per frame: {modem.tx_samples_per_frame}")
        print("OK")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        modem.close()


if __name__ == "__main__":
    raise SystemExit(main())
