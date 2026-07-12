"""Channel-busy heuristics for EasyPal-style Wait TX while QRM."""

from __future__ import annotations


def channel_looks_busy(
    *,
    level: int | None,
    snr_db: float | None,
    fac_locked: bool,
    qrm_level: int = 35,
    qrm_snr_db: float = 2.0,
) -> bool:
    """Return True when the channel appears occupied.

    EasyPal delays TX when audio level is high or (with FAC lock) SNR suggests
    another station is already on frequency.
    """
    if level is not None and int(level) >= int(qrm_level):
        return True
    if fac_locked and snr_db is not None and float(snr_db) >= float(qrm_snr_db):
        return True
    return False
