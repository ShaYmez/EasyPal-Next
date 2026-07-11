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
        self._tx_carry = np.array([], dtype=np.int16)
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
        if self._on_rx is not None:
            chunk = indata.copy().reshape(-1)
            if chunk.dtype != np.int16:
                chunk = (np.clip(chunk, -1.0, 1.0) * 32767.0).astype(np.int16)
            self._on_rx(chunk)

    def _output_callback(self, outdata: np.ndarray, frames: int, time, status) -> None:  # noqa: ARG002
        needed = frames
        out_offset = 0
        while needed > 0:
            if len(self._tx_carry) == 0:
                try:
                    self._tx_carry = self._tx_queue.get_nowait().astype(np.int16)
                except Empty:
                    outdata[out_offset:, 0] = 0
                    return
            take = min(needed, len(self._tx_carry))
            outdata[out_offset : out_offset + take, 0] = (
                self._tx_carry[:take].astype(np.float32) / 32768.0
            )
            self._tx_carry = self._tx_carry[take:]
            out_offset += take
            needed -= take

    def start(self, on_rx: AudioChunkCallback) -> None:
        self._on_rx = on_rx
        self._input_stream = sd.InputStream(
            device=self._input_device,
            channels=1,
            dtype="float32",
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

    def clear_tx_buffer(self) -> None:
        while True:
            try:
                self._tx_queue.get_nowait()
            except Empty:
                break
        self._tx_carry = np.array([], dtype=np.int16)

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
