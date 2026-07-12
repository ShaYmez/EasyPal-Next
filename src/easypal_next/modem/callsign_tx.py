"""Callsign helpers and on-air WFTxt header audio."""

from __future__ import annotations

import threading

import numpy as np
from PIL import Image

from easypal_next.config.schema import AppConfig, WaterfallConfig
from easypal_next.waterfall.encoder import SpectrumPainterEncoder
from easypal_next.waterfall.text_renderer import render_text_bitmap
from easypal_next.waterfall.tx_pcm import play_waterfall_pcm

DEFAULT_CALLSIGN = "N0CALL"

# Readable on-air callsign paint (EasyPal-style banner, stretched in time).
_CALLSIGN_FONT_SIZE = 40
_CALLSIGN_LINE_TIME_MS = 50.0
_CALLSIGN_LINE_REPEATS = 2
_CALLSIGN_TARGET_SECONDS = 5.5


def effective_callsign(config: AppConfig | str | None) -> str:
    if isinstance(config, str) or config is None:
        raw = config or ""
    else:
        raw = config.callsign or ""
    trimmed = raw.strip().upper()
    return trimmed if trimmed else DEFAULT_CALLSIGN


def callsign_header_text(callsign: str) -> str:
    """EasyPal-style banner so short calls still paint a wide glyph."""
    call = (callsign or DEFAULT_CALLSIGN).strip().upper() or DEFAULT_CALLSIGN
    return f"<< {call} >>"


def _callsign_waterfall_config(base: WaterfallConfig) -> WaterfallConfig:
    return base.model_copy(
        update={
            "line_time_ms": _CALLSIGN_LINE_TIME_MS,
            "line_repeats": _CALLSIGN_LINE_REPEATS,
            "default_font_size": max(_CALLSIGN_FONT_SIZE, int(base.default_font_size)),
            "negative_paint": False,
        }
    )


def build_callsign_wftxt_audio(config: AppConfig) -> np.ndarray:
    """Encode callsign as WFTxt lasting about ``_CALLSIGN_TARGET_SECONDS``.

    Short calls like M0VUB only ink ~1 s at body WFTxt settings; we render a
    banner and duplicate painted columns so the waterfall shows solid glyphs.
    """
    call = effective_callsign(config)
    # Repeat banner so total ink time stays high even with letter gaps.
    text = f"{callsign_header_text(call)}   {callsign_header_text(call)}"
    wf = _callsign_waterfall_config(config.waterfall)
    bitmap = render_text_bitmap(
        text,
        font_name=wf.default_font,
        font_size=wf.default_font_size,
        freq_min_hz=wf.freq_min_hz,
        freq_max_hz=wf.freq_max_hz,
        negative=False,
        min_columns=8,
    )
    pixels = np.array(bitmap, dtype=np.uint8)
    # Keep only columns that carry paint, then tile them to the target width.
    ink = np.any(pixels > 0, axis=0)
    if np.any(ink):
        solid = pixels[:, ink]
    else:
        solid = pixels
    repeats = max(1, int(wf.line_repeats))
    target_cols = max(
        solid.shape[1],
        int(round(_CALLSIGN_TARGET_SECONDS * 1000.0 / float(wf.line_time_ms) / repeats)),
    )
    reps = max(1, int(np.ceil(target_cols / max(1, solid.shape[1]))))
    tiled = np.tile(solid, (1, reps))[:, :target_cols]
    # Small silent margins so the burst does not click on/off abruptly.
    margin = np.zeros((tiled.shape[0], 6), dtype=np.uint8)
    framed = np.concatenate([margin, tiled, margin], axis=1)
    stretched = Image.fromarray(framed, mode="L")
    encoder = SpectrumPainterEncoder(wf)
    return encoder._bitmap_to_audio(stretched)  # noqa: SLF001


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
    """Play int16 mono PCM; honour optional stop_event.

    Defaults to WinMM on Windows so HamDRM loopback preview stays PortAudio-free.
    """
    import sys

    backend = "winmm" if sys.platform == "win32" else "portaudio"
    play_waterfall_pcm(
        samples,
        sample_rate=sample_rate,
        play_sample_rate=play_sample_rate or sample_rate,
        output_device=output_device,
        stop_event=stop_event,
        event_bus=event_bus,
        waterfall=waterfall,
        spectrum_source="tx",
        backend=backend,  # type: ignore[arg-type]
    )
