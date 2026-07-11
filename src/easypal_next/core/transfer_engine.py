"""TX/RX orchestration state machine."""

from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from easypal_next.audio.modem_bridge import ModemBridge
from easypal_next.audio.resampler import downsample_to_modem
from easypal_next.audio.waterfall_tap import WaterfallTap
from easypal_next.config.schema import AppConfig
from easypal_next.core.events import (
    EventBus,
    GalleryUpdatedEvent,
    LogEvent,
    RxImageReadyEvent,
    SessionStateChangedEvent,
    SpectrumEvent,
    TransferProgressEvent,
    WaterfallPaintStartedEvent,
)
from easypal_next.core.session import SessionState
from easypal_next.fec.encoder import FecEncoder
from easypal_next.fec.file_assembler import FileAssembler, FileMeta
from easypal_next.fec.meta_codec import pack_fec_shard, pack_file_meta, unpack_fec_shard, unpack_file_meta
from easypal_next.fec.packet import PacketType, frame_packet, parse_packet
from easypal_next.modem.framer import ModemFramer
from easypal_next.modem.interface import ModemInterface
from easypal_next.network.gallery_store import GalleryStore
from easypal_next.radio.controller import RadioController
from easypal_next.waterfall.encoder import SpectrumPainterEncoder


@dataclass
class TransferProgress:
    pct: float = 0.0
    bytes_done: int = 0
    bytes_total: int = 0


class TransferEngine:
    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        tx_modem: ModemInterface,
        rx_modem: ModemInterface,
        radio: RadioController,
        waterfall: SpectrumPainterEncoder,
        gallery: GalleryStore,
        modem_bridge: ModemBridge | None = None,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._tx_modem = tx_modem
        self._rx_modem = rx_modem
        self._radio = radio
        self._waterfall = waterfall
        self._gallery = gallery
        self._bridge = modem_bridge
        self._state = SessionState.IDLE
        self._progress = TransferProgress()
        self._abort = threading.Event()
        self._worker: threading.Thread | None = None
        self._assembler = FileAssembler()
        self._rx_output_dir = Path(".")
        self._seq = 0
        self._initialized = False
        self._rx_framer = ModemFramer(126)
        self._rx_listening = False
        self._bridge_tx_only = False
        self._spectrum_tap: WaterfallTap | None = None
        self._tx_file_path: Path | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    def set_modem_bridge(self, bridge: ModemBridge | None) -> None:
        if self._bridge and self._bridge.is_running:
            self._bridge.stop()
        self._bridge = bridge
        self._bridge_tx_only = False

    def start_audio_monitor(self) -> None:
        """Open the sound card for live RX spectrum (on-air only)."""
        if self._config.transfer.loopback_mode or not self._bridge:
            return
        if not self._initialized:
            self.initialize()
        else:
            self._open_audio_devices()
        self._bridge_tx_only = False
        self._ensure_bridge_running()

    def _resume_audio_monitor_if_on_air(self) -> None:
        if self._config.transfer.loopback_mode or not self._bridge:
            return
        if self._rx_listening or self._state == SessionState.TUNING:
            return
        if self._state not in (
            SessionState.IDLE,
            SessionState.RX_DONE,
            SessionState.TX_DONE,
            SessionState.ERROR,
        ):
            return
        self._ensure_bridge_running()

    def get_progress(self) -> TransferProgress:
        return self._progress

    def initialize(self) -> None:
        if self._initialized:
            return
        self._tx_modem.open(self._config.modem.mode, self._config.modem.sample_rate)
        self._rx_modem.open(self._config.modem.mode, self._config.modem.sample_rate)
        self._rx_framer = ModemFramer(self._rx_modem.frame_payload_size)
        self._rx_modem.set_frame_rx_callback(self._on_modem_subframe)
        if not self._config.transfer.loopback_mode:
            self._radio.connect()
            self._open_audio_devices()
        self._initialized = True
        self._event_bus.publish(LogEvent(level="info", message="Transfer engine initialized"))

    def _open_audio_devices(self) -> None:
        if not self._bridge:
            return
        if self._bridge.is_running:
            self._bridge.stop()
        self._bridge._audio.open(  # noqa: SLF001
            self._config.audio.input_device,
            self._config.audio.output_device,
            self._config.audio.sample_rate,
            self._config.audio.block_size,
        )

    def _ensure_bridge_running(self, tx_only: bool = False) -> None:
        if self._config.transfer.loopback_mode or not self._bridge:
            return
        if not self._bridge.is_running:
            self._bridge.start()
            if tx_only:
                self._bridge_tx_only = True

    def _maybe_stop_bridge(self) -> None:
        if self._config.transfer.loopback_mode or not self._bridge:
            return
        if self._rx_listening:
            return
        if self._bridge.is_running:
            self._bridge.stop()
        self._bridge_tx_only = False
        self._resume_audio_monitor_if_on_air()

    def _spectrum_callback(self, bins: list[float]) -> None:
        self._event_bus.publish(
            SpectrumEvent(bins=bins, sample_rate=self._tx_modem.modem_sample_rate)
        )

    def _ensure_spectrum_tap(self) -> WaterfallTap:
        if self._spectrum_tap is None:
            self._spectrum_tap = WaterfallTap(on_spectrum=self._spectrum_callback)
        return self._spectrum_tap

    def _feed_spectrum(self, audio: np.ndarray) -> None:
        if len(audio) == 0:
            return
        live_tx = self._state in (
            SessionState.TUNING,
            SessionState.TX_ARMED,
            SessionState.TX_WATERFALL_HEADER,
            SessionState.TX_ACTIVE,
            SessionState.TX_WATERFALL_FOOTER,
        )
        monitor = (
            self._config.waterfall.tx_monitor
            or self._config.transfer.loopback_mode
            or live_tx
        )
        if not monitor:
            return
        self._ensure_spectrum_tap().feed(audio)

    def _add_tx_gallery_entry(self, file_path: Path) -> None:
        entry = self._gallery.add_image(file_path, callsign=self._config.callsign, direction="tx")
        self._event_bus.publish(GalleryUpdatedEvent(image_id=entry.id, path=str(file_path)))

    def _set_state(self, state: SessionState) -> None:
        self._state = state
        self._event_bus.publish(SessionStateChangedEvent(state=state))

    def _update_progress(self, done: int, total: int) -> None:
        self._progress.bytes_done = done
        self._progress.bytes_total = total
        pct = (done / total * 100.0) if total else 0.0
        self._progress.pct = pct
        self._event_bus.publish(TransferProgressEvent(pct=pct, bytes_done=done, bytes_total=total))

    def _on_modem_subframe(self, payload: bytes) -> None:
        packet = self._rx_framer.feed(payload)
        if packet is None:
            return
        self._on_modem_rx(packet)

    def _on_modem_rx(self, payload: bytes) -> None:
        try:
            ptype, _seq, _total, body = parse_packet(payload)
        except ValueError:
            return
        if ptype == PacketType.FILE_META:
            meta, chunk_size = unpack_file_meta(body)
            self._assembler.set_meta(meta, chunk_size)
            self._set_state(SessionState.RX_ASSEMBLING)
            self._event_bus.publish(LogEvent(level="info", message=f"RX meta: {meta.filename}"))
        elif ptype == PacketType.FEC_SHARD:
            chunk_id, shard_index, data = unpack_fec_shard(body)
            if self._assembler.add_shard(chunk_id, shard_index, data):
                chunk_count = self._assembler.meta.chunk_count if self._assembler.meta else 0
                self._update_progress(len(self._assembler._chunks), chunk_count)  # noqa: SLF001
        elif ptype == PacketType.TX_COMPLETE:
            self._finalize_rx()

    def _finalize_rx(self) -> None:
        if not self._assembler.is_complete() or self._assembler.meta is None:
            return
        meta = self._assembler.meta
        out_path = self._rx_output_dir / meta.filename
        try:
            self._assembler.write_file(out_path)
        except (ValueError, RuntimeError) as exc:
            self._event_bus.publish(LogEvent(level="error", message=str(exc)))
            self._set_state(SessionState.ERROR)
            return
        self._event_bus.publish(RxImageReadyEvent(path=str(out_path)))
        entry = self._gallery.add_image(out_path, callsign=self._config.callsign, direction="rx")
        self._event_bus.publish(GalleryUpdatedEvent(image_id=entry.id, path=str(out_path)))
        self._event_bus.publish(LogEvent(level="info", message=f"RX complete: {out_path.name}"))
        self._set_state(SessionState.RX_DONE)
        self._set_state(SessionState.IDLE)

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _encode_modem_burst(self, packet: bytes) -> np.ndarray:
        framer = ModemFramer(self._tx_modem.frame_payload_size)
        subframes = framer.fragment(packet)
        parts: list[np.ndarray] = []
        for subframe in subframes:
            if hasattr(self._tx_modem, "encode_preamble"):
                parts.append(self._tx_modem.encode_preamble())
            parts.append(self._tx_modem.encode_frame(subframe))
            if hasattr(self._tx_modem, "encode_postamble"):
                parts.append(self._tx_modem.encode_postamble())
        return np.concatenate(parts) if parts else np.array([], dtype=np.int16)

    def _send_packet(self, ptype: PacketType, body: bytes, total: int = 1) -> np.ndarray:
        framed = frame_packet(ptype, self._next_seq(), total, body)
        return self._encode_modem_burst(framed)

    def _waterfall_to_modem(self, audio: np.ndarray) -> np.ndarray:
        return downsample_to_modem(
            audio,
            self._config.waterfall.sample_rate,
            self._tx_modem.modem_sample_rate,
        )

    def _play_or_buffer(self, audio: np.ndarray, loopback_buffer: list[np.ndarray]) -> None:
        self._feed_spectrum(audio)
        if self._config.transfer.loopback_mode:
            loopback_buffer.append(audio)
        elif self._bridge:
            self._bridge.queue_tx(audio)
        pace = self._config.transfer.pace_ms
        if pace > 0:
            time.sleep(pace / 1000.0)

    def _run_tx(self, file_path: Path) -> None:
        bridge_started_here = False
        try:
            if not self._config.transfer.loopback_mode:
                self._ensure_bridge_running(tx_only=True)
                bridge_started_here = self._bridge_tx_only and self._bridge is not None

            data = file_path.read_bytes()
            file_hash = hashlib.sha256(data).hexdigest()
            chunk_size = self._config.fec.chunk_size
            chunk_count = math.ceil(len(data) / chunk_size) if data else 1
            encoder = FecEncoder(self._config.fec)
            meta = FileMeta(
                filename=file_path.name,
                file_size=len(data),
                sha256=file_hash,
                chunk_count=chunk_count,
                fec_k=self._config.fec.k,
                fec_m=self._config.fec.m,
            )

            loopback_buffer: list[np.ndarray] = []
            if not self._config.transfer.loopback_mode:
                self._radio.ptt_on()

            if self._config.waterfall.enabled:
                self._set_state(SessionState.TX_WATERFALL_HEADER)
                msg = self._config.waterfall.begin_message.format(callsign=self._config.callsign)
                self._event_bus.publish(WaterfallPaintStartedEvent(message=msg))
                header = self._waterfall.text_to_audio(
                    msg,
                    font=self._config.waterfall.default_font,
                    font_size=self._config.waterfall.default_font_size,
                )
                self._play_or_buffer(self._waterfall_to_modem(header), loopback_buffer)

            self._set_state(SessionState.TX_ACTIVE)
            total_shards = chunk_count * self._config.fec.m
            shards_sent = 0

            meta_audio = self._send_packet(PacketType.FILE_META, pack_file_meta(meta, chunk_size))
            self._play_or_buffer(meta_audio, loopback_buffer)

            for chunk_id in range(chunk_count):
                if self._abort.is_set():
                    break
                start = chunk_id * chunk_size
                chunk = data[start : start + chunk_size]
                shards = encoder.encode_chunk(chunk)
                for shard_index, shard in enumerate(shards):
                    if self._abort.is_set():
                        break
                    body = pack_fec_shard(chunk_id, shard_index, shard)
                    audio = self._send_packet(PacketType.FEC_SHARD, body, total=total_shards)
                    self._play_or_buffer(audio, loopback_buffer)
                    shards_sent += 1
                    self._update_progress(shards_sent, total_shards)

            complete_audio = self._send_packet(PacketType.TX_COMPLETE, b"")
            self._play_or_buffer(complete_audio, loopback_buffer)

            if self._config.waterfall.enabled and self._config.waterfall.end_message:
                self._set_state(SessionState.TX_WATERFALL_FOOTER)
                footer = self._waterfall.text_to_audio(
                    self._config.waterfall.end_message.format(callsign=self._config.callsign),
                    font=self._config.waterfall.default_font,
                    font_size=self._config.waterfall.default_font_size,
                )
                self._play_or_buffer(self._waterfall_to_modem(footer), loopback_buffer)

            if self._config.transfer.loopback_mode:
                rate = self._tx_modem.modem_sample_rate
                lead_silence = np.zeros(rate, dtype=np.int16)
                tail_silence = np.zeros(int(rate * 0.5), dtype=np.int16)
                loopback_buffer.insert(0, lead_silence)
                loopback_buffer.append(tail_silence)
                combined = np.concatenate(loopback_buffer)
                self._assembler = FileAssembler()
                self._rx_framer.reset()
                if self._rx_output_dir == Path("."):
                    self._rx_output_dir = self._gallery.received_dir()
                self._set_state(SessionState.RX_ASSEMBLING)
                self._rx_modem.decode_samples(combined)
                self._feed_spectrum(combined)
                self._finalize_rx()
            elif self._bridge:
                self._bridge.drain_tx()
                post_delay = getattr(self._config.radio, "post_tx_delay_ms", 200)
                time.sleep(post_delay / 1000.0)

            if not self._config.transfer.loopback_mode:
                self._radio.ptt_off()

            if self._tx_file_path is not None and not self._abort.is_set():
                self._add_tx_gallery_entry(self._tx_file_path)

            self._set_state(SessionState.TX_DONE)
            self._event_bus.publish(LogEvent(level="info", message="TX complete"))
            self._set_state(SessionState.IDLE)
        except Exception as exc:
            self._event_bus.publish(LogEvent(level="error", message=f"TX failed: {exc}"))
            self._set_state(SessionState.ERROR)
            self._set_state(SessionState.IDLE)
        finally:
            self._abort.clear()
            self._tx_file_path = None
            if bridge_started_here:
                self._maybe_stop_bridge()

    def _run_waterfall_tx(self, message: str) -> None:
        bridge_started_here = False
        try:
            if not self._config.waterfall.enabled:
                raise RuntimeError("Waterfall TX is disabled in settings")
            if not self._config.transfer.loopback_mode:
                self._ensure_bridge_running(tx_only=True)
                bridge_started_here = self._bridge_tx_only and self._bridge is not None
                self._radio.ptt_on()

            loopback_buffer: list[np.ndarray] = []
            self._set_state(SessionState.TX_WATERFALL_HEADER)
            self._event_bus.publish(WaterfallPaintStartedEvent(message=message))
            header = self._waterfall.text_to_audio(
                message,
                font=self._config.waterfall.default_font,
                font_size=self._config.waterfall.default_font_size,
            )
            self._play_or_buffer(self._waterfall_to_modem(header), loopback_buffer)

            if self._config.transfer.loopback_mode and loopback_buffer:
                combined = np.concatenate(loopback_buffer)
                self._feed_spectrum(combined)
            elif self._bridge:
                self._bridge.drain_tx()
                post_delay = getattr(self._config.radio, "post_tx_delay_ms", 200)
                time.sleep(post_delay / 1000.0)

            if not self._config.transfer.loopback_mode:
                self._radio.ptt_off()

            self._set_state(SessionState.TX_DONE)
            self._event_bus.publish(LogEvent(level="info", message="Waterfall text TX complete"))
            self._set_state(SessionState.IDLE)
        except Exception as exc:
            self._event_bus.publish(LogEvent(level="error", message=f"Waterfall TX failed: {exc}"))
            self._set_state(SessionState.ERROR)
            self._set_state(SessionState.IDLE)
        finally:
            self._abort.clear()
            if bridge_started_here:
                self._maybe_stop_bridge()

    def start_tx(self, file_path: Path) -> None:
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start TX from state {self._state}")
        self.initialize()
        self._abort.clear()
        self._seq = 0
        self._tx_file_path = file_path
        self._event_bus.publish(LogEvent(level="info", message=f"TX armed: {file_path}"))
        self._set_state(SessionState.TX_ARMED)
        self._worker = threading.Thread(target=self._run_tx, args=(file_path,), daemon=True)
        self._worker.start()

    def _encode_tune_burst(self) -> np.ndarray:
        if hasattr(self._tx_modem, "encode_preamble"):
            return self._tx_modem.encode_preamble()
        rate = self._tx_modem.modem_sample_rate
        return np.zeros(max(rate // 20, 1), dtype=np.int16)

    def _run_tune(self) -> None:
        bridge_started_here = False
        try:
            self._ensure_bridge_running(tx_only=True)
            bridge_started_here = self._bridge_tx_only and self._bridge is not None
            if not self._bridge:
                raise RuntimeError("Audio bridge unavailable — check audio devices in Settings")

            self._radio.ptt_on()
            self._set_state(SessionState.TUNING)
            emission = self._config.transfer.radio_emission.upper()
            self._event_bus.publish(
                LogEvent(
                    level="info",
                    message=f"Tune started ({emission}) — adjust drive/VOX; watch waterfall",
                )
            )
            deadline = time.monotonic() + self._config.transfer.tune_max_seconds
            while not self._abort.is_set() and time.monotonic() < deadline:
                audio = self._encode_tune_burst()
                self._feed_spectrum(audio)
                if self._bridge and not self._abort.is_set():
                    self._bridge.queue_tx(audio)
                time.sleep(0.002)

            if self._bridge:
                self._bridge.drain_tx()
            self._radio.ptt_off()
            if self._abort.is_set():
                self._event_bus.publish(LogEvent(level="warning", message="Tune aborted"))
            else:
                self._event_bus.publish(LogEvent(level="info", message="Tune finished"))
            self._set_state(SessionState.IDLE)
        except Exception as exc:
            self._event_bus.publish(LogEvent(level="error", message=f"Tune failed: {exc}"))
            self._set_state(SessionState.ERROR)
            self._set_state(SessionState.IDLE)
        finally:
            self._abort.clear()
            try:
                self._radio.ptt_off()
            except Exception:
                pass
            if bridge_started_here:
                self._maybe_stop_bridge()
            else:
                self._resume_audio_monitor_if_on_air()

    def start_tune(self) -> None:
        if self._config.transfer.loopback_mode:
            raise RuntimeError("Tune requires on-air mode — disable loopback in Settings")
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start Tune from state {self._state}")
        self.initialize()
        self._abort.clear()
        self._event_bus.publish(LogEvent(level="info", message="Tune armed"))
        self._worker = threading.Thread(target=self._run_tune, daemon=True)
        self._worker.start()

    def stop_tune(self) -> None:
        if self._state != SessionState.TUNING:
            return
        self._abort.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5.0)

    def start_waterfall_tx(self, message: str) -> None:
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start waterfall TX from state {self._state}")
        self.initialize()
        self._abort.clear()
        self._tx_file_path = None
        self._event_bus.publish(LogEvent(level="info", message="Waterfall text TX armed"))
        self._set_state(SessionState.TX_ARMED)
        self._worker = threading.Thread(target=self._run_waterfall_tx, args=(message,), daemon=True)
        self._worker.start()

    def start_rx(self, output_dir: Path) -> None:
        if self._state != SessionState.IDLE:
            raise RuntimeError(f"Cannot start RX from state {self._state}")
        self.initialize()
        self._rx_output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        self._assembler = FileAssembler()
        self._rx_framer.reset()
        self._abort.clear()
        self._rx_listening = True
        self._bridge_tx_only = False
        if not self._config.transfer.loopback_mode and self._bridge:
            self._ensure_bridge_running()
        self._event_bus.publish(LogEvent(level="info", message=f"RX listening: {output_dir}"))
        self._set_state(SessionState.RX_LISTEN)

    def abort(self) -> None:
        was_tuning = self._state == SessionState.TUNING
        self._abort.set()
        self._rx_listening = False
        if was_tuning and self._worker and self._worker.is_alive():
            self._worker.join(timeout=5.0)
            self._abort.clear()
            self._set_state(SessionState.IDLE)
            self._resume_audio_monitor_if_on_air()
            return
        if self._bridge:
            self._bridge.stop()
        self._bridge_tx_only = False
        if not self._config.transfer.loopback_mode:
            try:
                self._radio.ptt_off()
            except Exception:
                pass
        self._event_bus.publish(LogEvent(level="warning", message="Transfer aborted"))
        self._set_state(SessionState.IDLE)
        self._resume_audio_monitor_if_on_air()
