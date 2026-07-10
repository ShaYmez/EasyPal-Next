"""Enumerate serial COM ports for radio PTT / CAT configuration."""

from __future__ import annotations

import serial.tools.list_ports


def list_serial_ports() -> list[tuple[str, str]]:
    """Return (device, description) for each available serial port."""
    ports: list[tuple[str, str]] = []
    for info in serial.tools.list_ports.comports():
        device = info.device
        desc = info.description or device
        if "OpenGD77" in desc or "OpenGD77" in device:
            desc = f"OpenGD77 — {desc}"
        ports.append((device, desc))
    return sorted(ports, key=lambda item: item[0])
