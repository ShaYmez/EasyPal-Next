"""Play waterfall / WFTxt PCM on the sound card with optional spectrum feed."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from easypal_next.audio.waterfall_tap import WaterfallTap
from easypal_next.config.schema import AppConfig, WaterfallConfig
from easypal_next.core.events import EventBus, SpectrumEvent
from easypal_next.waterfall.cue_wav import resample_int16
from easypal_next.waterfall.encoder import SpectrumPainterEncoder
from easypal_next.waterfall.text_renderer import render_text_bitmap

PlayBackend = Literal["winmm", "portaudio"]


def _stretch_ink_bitmap(
    bitmap: Image.Image,
    *,
    line_time_ms: float,
    line_repeats: int,
    min_body_seconds: float,
) -> Image.Image:
    """Tile painted columns so short WFTxt lasts ~EasyPal cue length (~3.2 s).

    Silent ``min_columns`` padding alone leaves a brief glyph flash then hush;
    EasyPal program cues fill the whole ~3.3 s with ink.
    """
    pixels = np.array(bitmap, dtype=np.uint8)
    ink = np.any(pixels > 0, axis=0)
    if not np.any(ink):
        return bitmap
    solid = pixels[:, ink]
    repeats = max(1, int(line_repeats))
    target_cols = max(
        solid.shape[1],
        int(round(float(min_body_seconds) * 1000.0 / float(line_time_ms) / repeats)),
    )
    if solid.shape[1] >= target_cols:
        return bitmap
    reps = int(np.ceil(target_cols / max(1, solid.shape[1])))
    tiled = np.tile(solid, (1, reps))[:, :target_cols]
    margin = np.zeros((tiled.shape[0], 4), dtype=np.uint8)
    framed = np.concatenate([margin, tiled, margin], axis=1)
    return Image.fromarray(framed, mode="L")


def encode_waterfall_text(
    config: AppConfig,
    text: str,
    *,
    min_columns: int = 8,
) -> np.ndarray:
    """Encode WFTxt; stretch short messages to ``waterfall.min_body_seconds``."""
    wf = config.waterfall
    encoder = SpectrumPainterEncoder(wf)
    bitmap = render_text_bitmap(
        text,
        font_name=wf.default_font,
        font_size=wf.default_font_size,
        freq_min_hz=wf.freq_min_hz,
        freq_max_hz=wf.freq_max_hz,
        negative=bool(getattr(wf, "negative_paint", False)),
        min_columns=min_columns,
        slash_zeros=bool(getattr(wf, "slash_zeros", False)),
    )
    min_s = float(getattr(wf, "min_body_seconds", 3.2) or 0.0)
    if min_s > 0:
        bitmap = _stretch_ink_bitmap(
            bitmap,
            line_time_ms=float(wf.line_time_ms),
            line_repeats=int(wf.line_repeats),
            min_body_seconds=min_s,
        )
    return encoder._bitmap_to_audio(bitmap)  # noqa: SLF001


def encode_waterfall_image(config: AppConfig, image_path: Path) -> np.ndarray:
    """Encode a WFPic image (grayscale / RGB) to SpectrumPainter PCM."""
    encoder = SpectrumPainterEncoder(config.waterfall)
    return encoder.image_to_audio(Path(image_path))


def _feed_spectrum_while_playing(
    samples: np.ndarray,
    *,
    sample_rate: int,
    event_bus: EventBus,
    waterfall: WaterfallConfig,
    spectrum_source: str,
    stop_event: threading.Event | None,
    duration_s: float,
) -> None:
    """Publish TX SpectrumEvents paced to real time so the waterfall keeps rolling."""

    def _on_bins(bins: list[float]) -> None:
        event_bus.publish(
            SpectrumEvent(
                bins=bins,
                sample_rate=sample_rate,
                source=spectrum_source,  # type: ignore[arg-type]
            )
        )

    fft_size = max(256, min(2048, int(getattr(waterfall, "fft_size", 1024) or 1024)))
    # Smaller FFT + higher overlap → smoother glyph paint while scrolling.
    tap = WaterfallTap(
        fft_size=min(1024, fft_size),
        overlap=0.75,
        window="hann",
        on_spectrum=_on_bins,
    )
    hop = max(256, int(sample_rate * 0.03))
    t0 = time.monotonic()
    for offset in range(0, len(samples), hop):
        if stop_event is not None and stop_event.is_set():
            return
        tap.feed(samples[offset : offset + hop])
        target = t0 + (offset + hop) / float(sample_rate)
        delay = target - time.monotonic()
        if delay > 0.001:
            time.sleep(min(delay, 0.04))
    # Hold until audio should be finished (winsound async / PortAudio drain).
    while time.monotonic() - t0 < duration_s:
        if stop_event is not None and stop_event.is_set():
            return
        time.sleep(0.02)


def play_waterfall_pcm(
    samples: np.ndarray,
    *,
    sample_rate: int,
    output_device: int | None,
    stop_event: threading.Event | None = None,
    event_bus: EventBus | None = None,
    waterfall: WaterfallConfig | None = None,
    spectrum_source: str = "tx",
    play_sample_rate: int | None = None,
    backend: PlayBackend = "portaudio",
) -> None:
    """Play int16 mono PCM; optionally publish TX SpectrumEvents while playing.

    ``sample_rate`` is the rate of ``samples``. For ``backend="portaudio"``, if
    ``play_sample_rate`` differs, audio is resampled for output. For
    ``backend="winmm"``, samples play at their native ``sample_rate`` (preferred
    for HamDRM — avoids PortAudio + 25→48 kHz resample).
    """
    if samples is None or len(samples) == 0:
        return

    play_samples = samples
    out_rate = int(sample_rate)
    if backend == "portaudio":
        out_rate = int(play_sample_rate or sample_rate)
        if out_rate != sample_rate:
            play_samples = resample_int16(samples, sample_rate, out_rate)

    duration_s = len(play_samples) / float(out_rate)
    feed_spectrum = (
        event_bus is not None
        and waterfall is not None
        and bool(waterfall.live_enabled)
        and bool(getattr(waterfall, "tx_monitor", True))
    )

    if backend == "winmm":
        from easypal_next.waterfall.winmm_play import play_pcm_winmm

        feeder: threading.Thread | None = None
        if feed_spectrum:
            assert event_bus is not None and waterfall is not None
            feeder = threading.Thread(
                target=_feed_spectrum_while_playing,
                kwargs={
                    "samples": play_samples,
                    "sample_rate": out_rate,
                    "event_bus": event_bus,
                    "waterfall": waterfall,
                    "spectrum_source": spectrum_source,
                    "stop_event": stop_event,
                    "duration_s": duration_s,
                },
                name="wftxt-waterfall-tap",
                daemon=True,
            )
            feeder.start()
        try:
            play_pcm_winmm(
                play_samples,
                sample_rate=out_rate,
                stop_event=stop_event,
            )
        finally:
            if feeder is not None:
                feeder.join(timeout=duration_s + 1.0)
        return

    import sounddevice as sd

    audio = play_samples.astype(np.float32) / 32768.0
    # Extra device latency avoids underrun clicks beside WinMM/HamDRM.
    sd.play(
        audio,
        samplerate=out_rate,
        device=output_device,
        blocking=False,
        latency="high",
    )

    tap: WaterfallTap | None = None
    if feed_spectrum:
        assert event_bus is not None and waterfall is not None

        def _on_bins(bins: list[float]) -> None:
            event_bus.publish(
                SpectrumEvent(
                    bins=bins,
                    sample_rate=out_rate,
                    source=spectrum_source,  # type: ignore[arg-type]
                )
            )

        tap = WaterfallTap(
            fft_size=min(1024, max(256, int(getattr(waterfall, "fft_size", 1024) or 1024))),
            overlap=0.75,
            window="hann",
            on_spectrum=_on_bins,
        )

    hop = max(256, int(out_rate * 0.03))
    t0 = time.monotonic()
    try:
        for offset in range(0, len(play_samples), hop):
            if stop_event is not None and stop_event.is_set():
                sd.stop()
                return
            if tap is not None:
                tap.feed(play_samples[offset : offset + hop])
            target = t0 + (offset + hop) / float(out_rate)
            delay = target - time.monotonic()
            if delay > 0.001:
                time.sleep(min(delay, 0.04))
        while True:
            if stop_event is not None and stop_event.is_set():
                sd.stop()
                return
            remaining = len(audio) / float(out_rate) - (time.monotonic() - t0)
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))
        sd.wait()
    except Exception:
        try:
            sd.stop()
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        time.sleep(0.05)
