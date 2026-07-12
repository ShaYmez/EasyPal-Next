"""Play waterfall / WFTxt PCM on the sound card with optional spectrum feed."""

from __future__ import annotations

import threading
import time

import numpy as np

from easypal_next.audio.waterfall_tap import WaterfallTap
from easypal_next.config.schema import AppConfig, WaterfallConfig
from easypal_next.core.events import EventBus, SpectrumEvent
from easypal_next.waterfall.cue_wav import resample_int16
from easypal_next.waterfall.encoder import SpectrumPainterEncoder


def encode_waterfall_text(
    config: AppConfig,
    text: str,
    *,
    min_columns: int = 80,
) -> np.ndarray:
    encoder = SpectrumPainterEncoder(config.waterfall)
    return encoder.text_to_audio(
        text,
        font=config.waterfall.default_font,
        font_size=config.waterfall.default_font_size,
        min_columns=min_columns,
    )


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
) -> None:
    """Play int16 mono PCM; optionally publish TX SpectrumEvents while playing.

    ``sample_rate`` is the rate of ``samples``. If ``play_sample_rate`` differs
    (e.g. encode at 25 kHz, play at device 48 kHz), audio is resampled for output.
    """
    if samples is None or len(samples) == 0:
        return
    import sounddevice as sd

    out_rate = int(play_sample_rate or sample_rate)
    play_samples = samples
    if out_rate != sample_rate:
        play_samples = resample_int16(samples, sample_rate, out_rate)

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
    if event_bus is not None and waterfall is not None and waterfall.live_enabled:

        def _on_bins(bins: list[float]) -> None:
            event_bus.publish(
                SpectrumEvent(
                    bins=bins,
                    sample_rate=out_rate,
                    source=spectrum_source,  # type: ignore[arg-type]
                )
            )

        tap = WaterfallTap(
            fft_size=1024,
            overlap=0.5,
            window="hann",
            on_spectrum=_on_bins,
        )

    hop = max(512, int(out_rate * 0.05))
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
                time.sleep(min(delay, 0.05))
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
