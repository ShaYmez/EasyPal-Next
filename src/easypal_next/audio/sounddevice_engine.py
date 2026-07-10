"""sounddevice-backed audio engine."""

from __future__ import annotations

from collections.abc import Callable
from queue import Empty, Queue

import numpy as np
import sounddevice as sd

from easypal_next.audio.engine import AudioChunkCallback, AudioEngine


class SoundDeviceEngine(AudioEngine):
    def __init__(self) -> None:
        self._input_device: int | None = None
        self._output_device: int | None = None
        self._sample_rate = 48000
        self._block_size = 1024
        self._running = False
        self._on_rx: AudioChunkCallback | None = None
        self._tx_queue: Queue[np.ndarray] = Queue()
        self._input_stream: sd.InputStream | None = None
        self._output_stream: sd.OutputStream | None = None

    def list_devices(self) -> list[dict]:
        devices = []
        for index, device in enumerate(sd.query_devices()):
            devices.append(
                {
                    "index": index,
                    "name": device["name"],
                    "max_input_channels": device["max_input_channels"],
                    "max_output_channels": device["max_output_channels"],
                    "default_samplerate": device["default_samplerate"],
                }
            )
        return devices

    def open(
        self,
        input_device: int | None,
        output_device: int | None,
        sample_rate: int,
        block_size: int,
    ) -> None:
        self._input_device = input_device
        self._output_device = output_device
        self._sample_rate = sample_rate
        self._block_size = block_size

    def _input_callback(self, indata: np.ndarray, frames: int, time, status) -> None:  # noqa: ARG002
        if status and self._on_rx:
            pass
        if self._on_rx is not None:
            self._on_rx(indata.copy().reshape(-1))

    def _output_callback(self, outdata: np.ndarray, frames: int, time, status) -> None:  # noqa: ARG002
        try:
            chunk = self._tx_queue.get_nowait()
        except Empty:
            outdata.fill(0)
            return
        samples = chunk.astype(np.float32) / 32768.0
        if len(samples) < frames:
            outdata[: len(samples), 0] = samples
            outdata[len(samples) :, 0] = 0
        else:
            outdata[:, 0] = samples[:frames]

    def start(self, on_rx: AudioChunkCallback) -> None:
        self._on_rx = on_rx
        self._input_stream = sd.InputStream(
            device=self._input_device,
            channels=1,
            dtype="int16",
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            callback=self._input_callback,
        )
        self._output_stream = sd.OutputStream(
            device=self._output_device,
            channels=1,
            dtype="float32",
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            callback=self._output_callback,
        )
        self._input_stream.start()
        self._output_stream.start()
        self._running = True

    def write_tx(self, samples: np.ndarray) -> None:
        self._tx_queue.put(samples.astype(np.int16))

    def stop(self) -> None:
        if self._input_stream:
            self._input_stream.stop()
        if self._output_stream:
            self._output_stream.stop()
        self._running = False

    def close(self) -> None:
        self.stop()
        if self._input_stream:
            self._input_stream.close()
            self._input_stream = None
        if self._output_stream:
            self._output_stream.close()
            self._output_stream = None

    @property
    def is_running(self) -> bool:
        return self._running
