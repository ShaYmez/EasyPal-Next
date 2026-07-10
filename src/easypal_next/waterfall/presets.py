"""Default waterfall text presets."""

from __future__ import annotations

BEGIN_DEFAULT = "<< EASYPAL >>"
BSR_REQUEST = "**** BSR REQUEST ****"


def callsign_header(callsign: str) -> str:
    return f"{callsign} TX"
