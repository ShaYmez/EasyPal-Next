#!/usr/bin/env python3
"""Two-process on-air test helper using virtual audio cable (manual setup)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

print(
    "VB-Cable on-air test requires two EasyPal-Next instances:\n"
    "  1. Set transfer.loopback_mode: false in config\n"
    "  2. Route TX output -> CABLE Input, RX input <- CABLE Output\n"
    "  3. Instance A: Receive\n"
    "  4. Instance B: LoadPic + Transmit\n"
    "\nSee docs/on-air-test.md for full checklist.\n"
    "\nFor automated modem test without sound card, use:\n"
    "  python scripts/loopback-transfer.py\n"
)
