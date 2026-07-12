"""Callsign helpers and on-air WFTxt header audio."""

from __future__ import annotations

import threading

import numpy as np

from easypal_next.config.schema import AppConfig
from easypal_next.waterfall.tx_pcm import encode_waterfall_text, play_waterfall_pcm

DEFAULT_CALLSIGN = "N0CALL"


def effective_callsign(config: AppConfig | str | None) -> str:
    if isinstance(config, str) or config is None:
        raw = config or ""
    else:
        raw = config.callsign or ""
    trimmed = raw.strip().upper()
    return trimmed if trimmed else DEFAULT_CALLSIGN


def build_callsign_wftxt_audio(config: AppConfig) -> np.ndarray:
    """Encode the effective callsign as waterfall-text PCM for on-air TX."""
    return encode_waterfall_text(config, effective_callsign(config))


def play_pcm_blocking(
    samples: np.ndarray,
    *,
    sample_rate: int,
    output_device: int | None,
    stop_event: threading.Event | None = None,
    event_bus=None,
    waterfall=None,
    play_sample_rate: int | None = None,
) -> None:
    """Play int16 mono PCM on the output device; honour optional stop_event."""
    play_waterfall_pcm(
        samples,
        sample_rate=sample_rate,
        play_sample_rate=play_sample_rate,
        output_device=output_device,
        stop_event=stop_event,
        event_bus=event_bus,
        waterfall=waterfall,
        spectrum_source="tx",
    )
