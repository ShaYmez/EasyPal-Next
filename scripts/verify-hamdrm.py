#!/usr/bin/env python3
"""Smoke-test a 64-bit hamdrm.dll load via the EasyPal-Next ctypes bindings."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from easypal_next.modem.hamdrm_api import (  # noqa: E402
    candidate_hamdrm_paths,
    load_hamdrm,
    resolve_hamdrm_dll,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, help="Explicit hamdrm.dll path")
    args = parser.parse_args()

    path = args.dll
    if path is None:
        path = resolve_hamdrm_dll()
    if path is None:
        print("No hamdrm.dll found. Candidates:")
        for p in candidate_hamdrm_paths():
            print(f"  - {p}")
        return 1

    print(f"Loading: {path}")
    lib = load_hamdrm(path)
    print(f"getFatalErr={lib.getFatalErr()}")
    print(f"GetAudNumDevIn={lib.GetAudNumDevIn()}")
    print(f"GetAudNumDevOut={lib.GetAudNumDevOut()}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
