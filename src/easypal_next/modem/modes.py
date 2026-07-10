"""FreeDV mode registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModemModeProfile:
    name: str
    description: str
    default: bool = False


MODEM_MODES: dict[str, ModemModeProfile] = {
    "DATAC3": ModemModeProfile("DATAC3", "HF OFDM data (EasyPal-class)", default=True),
    "DATAC4": ModemModeProfile("DATAC4", "HF OFDM data (higher rate)"),
    "FSK_LDPC": ModemModeProfile("FSK_LDPC", "VHF/UHF FSK with LDPC"),
}
