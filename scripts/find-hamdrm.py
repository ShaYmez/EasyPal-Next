#!/usr/bin/env python3
"""Locate HamDRM-compatible DLLs and report bitness / loadability."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from easypal_next.modem.hamdrm_api import (  # noqa: E402
    HamDrmUnavailable,
    candidate_hamdrm_paths,
    load_hamdrm,
    pe_bitness_label,
    pe_machine,
    python_is_64bit,
    resolve_hamdrm_dll,
)


def main() -> int:
    configured = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"Python: {sys.version.split()[0]} ({'64-bit' if python_is_64bit() else '32-bit'})")
    print(f"Platform: {platform.platform()}")
    print()
    print("Candidates (in search order):")
    seen_existing = False
    for path in candidate_hamdrm_paths(configured):
        exists = path.is_file()
        if exists:
            seen_existing = True
            machine = pe_machine(path)
            bits = pe_bitness_label(machine)
            print(f"  FOUND  {path}  [{bits}]")
            try:
                load_hamdrm(path)
                print("         loadable: YES")
            except HamDrmUnavailable as exc:
                print(f"         loadable: NO — {exc}")
            except OSError as exc:
                print(f"         loadable: NO — {exc}")
        else:
            print(f"  miss   {path}")

    print()
    resolved = resolve_hamdrm_dll(configured)
    if resolved is None:
        print("resolve_hamdrm_dll: None")
        return 1 if not seen_existing else 0
    print(f"resolve_hamdrm_dll: {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
