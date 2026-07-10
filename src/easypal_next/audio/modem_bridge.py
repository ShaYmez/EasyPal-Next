"""Bridge between sound card audio and modem sample rates."""

from __future__ import annotations

import threading
from collections.abc import Callable
from queue import Empty, Queue

import numpy as np

from easypal_next.audio.engine import AudioEngine
from easypal_next.audio.resampler import downsample_to_modem, upsample_from_modem
from easypal_next.audio.waterfall_tap import WaterfallTap
from easypal_next.modem.interface import ModemInterface

SpectrumCallback = Callable[[list[float]], None]


class ModemBridge:
    """Queues TX modem audio and feeds RX audio into the modem decoder."""

    def __init__(
        self,
        audio: AudioEngine,
        modem: ModemInterface,
        audio_rate: int,
        modem_rate: int,
        on_spectrum: SpectrumCallback | None = None,
    ) -> None:
        self._audio = audio
        self._modem = modem
        self._audio_rate = audio_rate
        self._modem_rate = modem_rate
        self._tx_queue: Queue[np.ndarray] = Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._waterfall_tap = WaterfallTap(on_spectrum=on_spectrum) if on_spectrum else None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._audio.start(self._on_audio_rx)
        self._thread = threading.Thread(target=self._tx_worker, name="modem-bridge-tx", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._audio.stop()

    def queue_tx(self, samples: np.ndarray) -> None:
        """Queue int16 modem-rate samples for upsampling and playback."""
        self._tx_queue.put(samples.astype(np.int16))

    def _on_audio_rx(self, samples: np.ndarray) -> None:
        if self._waterfall_tap:
            self._waterfall_tap.feed(samples)
        modem_samples = downsample_to_modem(samples, self._audio_rate, self._modem_rate)
        self._modem.decode_samples(modem_samples)

    def _tx_worker(self) -> None:
        while self._running:
            try:
                samples = self._tx_queue.get(timeout=0.05)
            except Empty:
                continue
            upsampled = upsample_from_modem(samples, self._modem_rate, self._audio_rate)
            self._audio.write_tx(upsampled)

    def inject_rx(self, samples: np.ndarray) -> None:
        """Feed modem-rate samples directly (loopback testing without sound card)."""
        self._modem.decode_samples(samples.astype(np.int16))

    def play_modem_tx(self, samples: np.ndarray) -> None:
        """Play modem-rate TX samples through audio output."""
        upsampled = upsample_from_modem(samples, self._modem_rate, self._audio_rate)
        self._audio.write_tx(upsampled)

    def drain_tx(self, timeout: float = 5.0) -> None:
        """Wait until queued TX audio has been written to the sound card."""
        deadline = timeout
        import time

        end = time.monotonic() + deadline
        while time.monotonic() < end:
            if self._tx_queue.empty():
                time.sleep(0.1)
                if self._tx_queue.empty():
                    return
            time.sleep(0.05)
