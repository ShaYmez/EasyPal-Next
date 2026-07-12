"""HamDRM transfer backend wrapping run.dll / hamdrm.dll via ctypes."""

from __future__ import annotations

import logging
import math
import shutil
import threading
import time
from ctypes import byref, c_char, c_float, c_int, create_string_buffer
from pathlib import Path

import numpy as np

from easypal_next.app.paths import user_data_dir
from easypal_next.config.schema import AppConfig
from easypal_next.core.events import (
    EventBus,
    GalleryUpdatedEvent,
    LogEvent,
    RxImageReadyEvent,
    SessionStateChangedEvent,
    SpectrumEvent,
    SyncStatusEvent,
    TransferProgressEvent,
    WaterfallPaintStartedEvent,
)
from easypal_next.core.session import SessionState
from easypal_next.modem.callsign_tx import (
    build_callsign_wftxt_audio,
    effective_callsign,
    play_pcm_blocking,
)
from easypal_next.modem.hamdrm_api import (
    SPECTRUM_BINS,
    HamDrmUnavailable,
    encode_c_path,
    encode_callsign,
    interleave_constant,
    load_hamdrm,
    mode_constant,
    mscprot_constant,
    qam_constant,
    resolve_hamdrm_dll,
    specocc_constant,
)
from easypal_next.modem.transfer_backend import SyncState, TransferBackend
from easypal_next.network.gallery_store import GalleryStore
from easypal_next.radio.controller import RadioController
from easypal_next.waterfall.cue_wav import load_tune_pcm
from easypal_next.waterfall.tx_pcm import encode_waterfall_text, play_waterfall_pcm

logger = logging.getLogger(__name__)

# GetState layout used by EasyPal / WinDRM UIs: IO, Time, Frame, FAC, MSC
_STATE_IO = 0
_STATE_TIME = 1
_STATE_FRAME = 2
_STATE_FAC = 3
_STATE_MSC = 4
_STATE_LEN = 8

# GetInputSpec: 2048-point rFFT after /2 decimation from 48 kHz → ~24 kHz.
# First 500 of 512 bins cover ~0–6 kHz; publish as if sample_rate=12 kHz.
HAMDRM_SPECTRUM_SAMPLE_RATE = 12_000
_SPECTRUM_INTERVAL_S = 0.15
_SYNC_EVERY_N = 4  # ~600 ms
_EPS = 1e-12

_MODE_LABELS = {0: "A", 1: "B", 2: "E"}
_SPECOCC_LABELS = {0: "2.3", 1: "2.5"}
_QAM_LABELS = {0: "4", 1: "16", 2: "64"}
_INTERLEAVE_LABELS = {0: "short", 1: "long"}
_MSCPROT_LABELS = {0: "normal", 1: "low"}


def linear_spectrum_to_db(bins: list[float]) -> list[float]:
    """Convert HamDRM GetSpectrum linear magnitudes to dB for the UI."""
    return [20.0 * math.log10(max(float(x), 0.0) + _EPS) for x in bins]


class HamDrmBackend(TransferBackend):
    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        gallery: GalleryStore,
        radio: RadioController | None = None,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._gallery = gallery
        self._radio = radio
        self._lib = None
        self._dll_path: Path | None = None
        self._available: bool | None = None
        self._unavailable_reason: str | None = None
        self._rx_active = False
        self._rx_paused_for_pcm = False
        self._threads_started = False
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._seen_rx: set[str] = set()
        self._lock = threading.RLock()
        self._tuning = False
        self._tune_stop = threading.Event()
        self._tune_thread: threading.Thread | None = None
        self._tx_active = False
        self._tx_poll_stop = threading.Event()
        self._tx_poll_thread: threading.Thread | None = None
        self._wftxt_busy = False
        self._wftxt_stop = threading.Event()
        self._wftxt_thread: threading.Thread | None = None

    @property
    def engine_name(self) -> str:
        return "hamdrm"

    @property
    def is_tuning(self) -> bool:
        return self._tuning

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            self._ensure_lib()
            self._available = True
            self._unavailable_reason = None
        except HamDrmUnavailable as exc:
            self._available = False
            self._unavailable_reason = str(exc)
            logger.warning("HamDRM unavailable: %s", exc)
        return self._available

    def unavailable_reason(self) -> str | None:
        self.is_available()
        return self._unavailable_reason

    def _ensure_lib(self):
        if self._lib is not None:
            return self._lib
        configured = self._config.modem.hamdrm_dll_path
        path = resolve_hamdrm_dll(configured)
        if path is None:
            raise HamDrmUnavailable(
                "HamDRM DLL not found. Install EasyPal (provides "
                r"C:\Program Files\EasyPal\run.dll) or place hamdrm.dll in "
                f"{user_data_dir()} / packaging redist. "
                "Note: stock EasyPal run.dll is 32-bit and will not load into 64-bit Python."
            )
        self._lib = load_hamdrm(path)
        self._dll_path = path
        return self._lib

    def _require_lib(self):
        if not self.is_available():
            reason = self._unavailable_reason or "HamDRM engine is unavailable"
            raise HamDrmUnavailable(reason)
        return self._ensure_lib()

    def _apply_tx_params(self) -> None:
        lib = self._require_lib()
        modem = self._config.modem
        lib.SetCall(encode_callsign(effective_callsign(self._config)))
        lib.SetParams(
            mode_constant(modem.hamdrm_mode),
            specocc_constant(modem.hamdrm_specocc),
            mscprot_constant(modem.hamdrm_mscprot),
            qam_constant(modem.hamdrm_qam),
            interleave_constant(modem.hamdrm_interleave),
        )
        lib.SetDCFreq(int(modem.hamdrm_dc_freq))
        lib.SetStartDelay(int(modem.hamdrm_start_delay))

    def _apply_paths(self) -> None:
        lib = self._require_lib()
        rx_dir = self._gallery.received_dir()
        rx_dir.mkdir(parents=True, exist_ok=True)
        corrupt = user_data_dir() / "corrupt"
        bsr = user_data_dir() / "bsr"
        corrupt.mkdir(parents=True, exist_ok=True)
        bsr.mkdir(parents=True, exist_ok=True)
        # Trailing separator helps some EasyPal builds treat the arg as a directory.
        lib.SetRXFileSavePath(encode_c_path(str(rx_dir) + "\\"))
        lib.SetRXCorruptSavePath(encode_c_path(str(corrupt) + "\\"))
        lib.SetBSRPath(encode_c_path(str(bsr) + "\\"))

    def _normalize_device_name(self, name: str) -> str:
        return " ".join(name.lower().replace("(mapped)", "").split())

    def _winmm_device_by_name(self, which: str, preferred_name: str | None) -> int:
        """Map a PortAudio-style device name onto a WinMM index used by the DLL."""
        lib = self._require_lib()
        if which == "in":
            count = int(lib.GetAudNumDevIn())
            get_name = lib.GetAudDeviceNameIn
        else:
            count = int(lib.GetAudNumDevOut())
            get_name = lib.GetAudDeviceNameOut
        if count <= 0:
            return 0
        if not preferred_name:
            return 0
        needle = self._normalize_device_name(preferred_name)
        for index in range(count):
            raw = get_name(index)
            if not raw:
                continue
            label = raw.decode("mbcs", errors="replace") if isinstance(raw, bytes) else str(raw)
            hay = self._normalize_device_name(label)
            if needle == hay or needle in hay or hay in needle:
                return index
        return 0

    def _sounddevice_name(self, which: str) -> str | None:
        """Resolve configured PortAudio device index to a device name."""
        cfg = self._config.audio
        index = cfg.input_device if which == "in" else cfg.output_device
        if index is None:
            return None
        try:
            from easypal_next.audio.sounddevice_engine import SoundDeviceEngine

            for device in SoundDeviceEngine().list_devices():
                if int(device["index"]) == int(index):
                    return str(device["name"])
        except Exception:  # noqa: BLE001 — fall back to WinMM 0
            logger.debug("Could not resolve sounddevice name for %s=%s", which, index, exc_info=True)
        return None

    def _audio_device_id(self, which: str) -> int:
        """Return WinMM device index for HamDRM (not PortAudio index)."""
        return self._winmm_device_by_name(which, self._sounddevice_name(which))

    def _should_play_callsign_header(self) -> bool:
        return (
            bool(self._config.transfer.require_callsign_wftxt_header)
            and not self._config.transfer.loopback_mode
        )

    def _set_ui_state(self, state: SessionState) -> None:
        self._event_bus.publish(SessionStateChangedEvent(state=state))

    def _pcm_sample_rate(self) -> int:
        return int(self._config.waterfall.sample_rate or self._config.audio.sample_rate)

    def _pause_rx_for_pcm(self) -> None:
        """Release WinMM capture so PortAudio can play WFTxt / Tune safely."""
        # Flag first so the GUI spectrum timer skips DLL calls mid-flight.
        self._rx_paused_for_pcm = True
        time.sleep(0.12)
        with self._lock:
            if self._rx_active and self._lib is not None:
                try:
                    self._lib.ControlRX(False)
                except OSError as exc:
                    logger.warning("Pause RX for PCM failed: %s", exc)
        time.sleep(0.15)

    def _resume_rx_after_pcm(self) -> None:
        time.sleep(0.1)
        with self._lock:
            try:
                if self._rx_active and self._lib is not None:
                    self._lib.ControlRX(True)
            except OSError as exc:
                logger.warning("Resume RX after PCM failed: %s", exc)
            self._rx_paused_for_pcm = False

    def _ptt_on(self) -> None:
        if self._radio is None or self._config.transfer.loopback_mode:
            return
        try:
            self._radio.connect()
            self._radio.ptt_on()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PTT on failed: %s", exc)

    def _ptt_off(self) -> None:
        if self._radio is None:
            return
        try:
            post = getattr(self._config.radio, "post_tx_delay_ms", 200)
            if post:
                time.sleep(post / 1000.0)
            self._radio.ptt_off()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PTT off failed: %s", exc)

    def _play_pcm_on_air(
        self,
        pcm: np.ndarray,
        *,
        stop_event: threading.Event | None = None,
        ui_state: SessionState = SessionState.TX_WATERFALL_HEADER,
        pcm_sample_rate: int | None = None,
    ) -> None:
        if pcm is None or len(pcm) == 0:
            return
        self._set_ui_state(ui_state)
        self._pause_rx_for_pcm()
        # WFTxt is encoded at waterfall.sample_rate (25 kHz); Tune PCM is at
        # the device rate. Always pass the true rate of ``pcm`` — using the
        # paint rate for Tune was pitch-shifting tones off the green markers.
        src_rate = int(pcm_sample_rate or self._pcm_sample_rate())
        play_rate = int(self._config.audio.sample_rate)
        try:
            play_waterfall_pcm(
                pcm,
                sample_rate=src_rate,
                play_sample_rate=play_rate,
                output_device=self._config.audio.output_device,
                stop_event=stop_event,
                event_bus=self._event_bus,
                waterfall=self._config.waterfall,
                spectrum_source="tx",
            )
        finally:
            self._resume_rx_after_pcm()

    def _header_gap(self, stop_event: threading.Event | None = None) -> None:
        gap = float(getattr(self._config.transfer, "callsign_header_gap_seconds", 1.0))
        if gap <= 0:
            return
        deadline = time.monotonic() + gap
        while time.monotonic() < deadline:
            if stop_event is not None and stop_event.is_set():
                return
            time.sleep(0.05)

    def _play_callsign_header(self, stop_event: threading.Event | None = None) -> None:
        if not self._should_play_callsign_header():
            return
        call = effective_callsign(self._config)
        self._event_bus.publish(
            LogEvent(level="info", message=f"On-air callsign header: {call}")
        )
        self._event_bus.publish(WaterfallPaintStartedEvent(message=call))
        pcm = build_callsign_wftxt_audio(self._config)
        self._play_pcm_on_air(pcm, stop_event=stop_event)
        if stop_event is None or not stop_event.is_set():
            self._header_gap(stop_event)

    def transmit_waterfall_text(self, message: str) -> None:
        """Play SpectrumPainter WFTxt PCM on the sound card (not via hamdrm.dll)."""
        text = (message or "").strip()
        if not text:
            raise ValueError("WFTxt message is empty")
        if self._tuning or self._tx_active or self._wftxt_busy:
            raise RuntimeError("Transfer already in progress")
        if self._config.transfer.loopback_mode:
            # Still play locally so operators can preview glyphs.
            pcm = encode_waterfall_text(self._config, text)
            play_pcm_blocking(
                pcm,
                sample_rate=self._pcm_sample_rate(),
                output_device=self._config.audio.output_device,
                event_bus=self._event_bus,
                waterfall=self._config.waterfall,
            )
            self._event_bus.publish(LogEvent(level="info", message=f"WFTxt preview: {text}"))
            return
        self._require_lib()
        self._wftxt_stop.clear()
        self._wftxt_busy = True
        self._wftxt_thread = threading.Thread(
            target=self._run_waterfall_text,
            args=(text,),
            name="hamdrm-wftxt",
            daemon=True,
        )
        self._wftxt_thread.start()

    def _run_waterfall_text(self, message: str) -> None:
        try:
            self._ptt_on()
            if self._should_play_callsign_header():
                self._play_callsign_header(stop_event=self._wftxt_stop)
            if self._wftxt_stop.is_set():
                return
            self._event_bus.publish(WaterfallPaintStartedEvent(message=message))
            self._event_bus.publish(LogEvent(level="info", message=f"WFTxt TX: {message}"))
            pcm = encode_waterfall_text(self._config, message)
            if len(pcm) == 0:
                raise RuntimeError("WFTxt encoder produced no audio")
            self._play_pcm_on_air(pcm, stop_event=self._wftxt_stop)
            if self._wftxt_stop.is_set():
                self._event_bus.publish(LogEvent(level="warning", message="WFTxt aborted"))
            else:
                self._event_bus.publish(LogEvent(level="info", message="WFTxt complete"))
        except Exception as exc:  # noqa: BLE001
            self._event_bus.publish(LogEvent(level="error", message=f"WFTxt failed: {exc}"))
        finally:
            self._ptt_off()
            self._wftxt_busy = False
            self._set_ui_state(SessionState.IDLE)

    def start_always_on_rx(self) -> None:
        lib = self._require_lib()
        with self._lock:
            if self._rx_active:
                return
            self._apply_tx_params()
            self._apply_paths()
            in_dev = self._audio_device_id("in")
            out_dev = self._audio_device_id("out")
            lib.SetAudDeviceIn(in_dev)
            lib.SetAudDeviceOut(out_dev)
            if not self._threads_started:
                lib.StartThreadRX(in_dev)
                self._threads_started = True
            lib.ControlRX(True)
            self._rx_active = True
            self._poll_stop.clear()
            self._poll_thread = threading.Thread(
                target=self._poll_rx_loop,
                name="hamdrm-rx-poll",
                daemon=True,
            )
            self._poll_thread.start()
        self._event_bus.publish(
            LogEvent(level="info", message=f"HamDRM always-on RX started ({self._dll_path})")
        )

    def stop_rx(self) -> None:
        if not self.is_available():
            return
        with self._lock:
            self._poll_stop.set()
            thread = self._poll_thread
            self._poll_thread = None
            if self._lib is not None and self._rx_active:
                try:
                    self._lib.ControlRX(False)
                except OSError as exc:
                    logger.warning("ControlRX(False) failed: %s", exc)
            self._rx_active = False
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

    def _publish_spectrum(self) -> None:
        """RX spectrum is polled on the Qt GUI thread — see ``poll_rx_spectrum``.

        Calling ``GetSpectrum`` from the HamDRM worker thread while Qt paints
        reliably segfaults the 64-bit DLL build; keep DLL spectrum reads off
        this poll loop.
        """
        return

    def poll_rx_spectrum(self) -> None:
        """Safe to call from the Qt main thread only."""
        if not self._config.waterfall.live_enabled:
            return
        if self._rx_paused_for_pcm or self._tuning or self._wftxt_busy or not self._rx_active:
            return
        try:
            with self._lock:
                if self._lib is None or not self._rx_active or self._rx_paused_for_pcm:
                    return
                buf = (c_float * SPECTRUM_BINS)()
                n = int(self._lib.GetSpectrum(buf))
                level = int(self._lib.GetLevel())
            if n <= 0:
                return
            count = min(n, SPECTRUM_BINS)
            bins = linear_spectrum_to_db([float(buf[i]) for i in range(count)])
        except Exception:  # noqa: BLE001
            return
        self._event_bus.publish(
            SpectrumEvent(
                bins=bins,
                sample_rate=HAMDRM_SPECTRUM_SAMPLE_RATE,
                source="rx",
                level_pct=level,
            )
        )
        # Also refresh sync LEDs from the GUI thread.
        try:
            self._publish_sync_status()
        except Exception:  # noqa: BLE001
            pass

    def _publish_sync_status(self) -> None:
        try:
            state = self.get_sync_state()
            percent_tx = None
            seg_pos = None
            if self._tx_active:
                with self._lock:
                    if self._lib is None:
                        return
                    pic = c_int(0)
                    pct = c_int(0)
                    done = bool(self._lib.GetPercentTX(byref(pic), byref(pct)))
                    percent_tx = int(pct.value)
                    seg_pos = int(pic.value)
                    if done:
                        percent_tx = 100
            self._event_bus.publish(
                SyncStatusEvent(
                    io=state.io,
                    time=state.time,
                    frame=state.frame,
                    fac=state.fac,
                    msc=state.msc,
                    snr_db=state.snr_db,
                    level=state.level,
                    dc_freq=state.dc_freq,
                    callsign=state.callsign,
                    mode=state.mode,
                    percent_tx=percent_tx,
                    seg_pos=seg_pos,
                )
            )
        except Exception:  # noqa: BLE001
            logger.debug("HamDRM sync publish failed", exc_info=True)

    def _poll_rx_loop(self) -> None:
        buf = create_string_buffer(260)
        tick = 0
        while not self._poll_stop.wait(_SPECTRUM_INTERVAL_S):
            try:
                if self._lib is None or self._rx_paused_for_pcm:
                    continue
                with self._lock:
                    if self._lib is None or not self._rx_active or self._rx_paused_for_pcm:
                        continue
                    fatal = int(self._lib.getFatalErr())
                if fatal:
                    self._event_bus.publish(
                        LogEvent(level="error", message=f"HamDRM fatal error code {fatal}")
                    )
                self._publish_spectrum()
                tick += 1
                # Sync/DLL status reads also belong on the GUI thread — see poll_rx_spectrum.
                if tick % _SYNC_EVERY_N == 0:
                    with self._lock:
                        if self._lib is None or not self._rx_active:
                            continue
                        got = bool(self._lib.GetFileRX(buf))
                    if got:
                        name = buf.value.decode("mbcs", errors="replace").strip()
                        if name and name not in self._seen_rx:
                            self._seen_rx.add(name)
                            self._ingest_rx_file(name)
            except Exception as exc:  # noqa: BLE001 — keep poll alive
                self._event_bus.publish(
                    LogEvent(level="error", message=f"HamDRM RX poll error: {exc}")
                )

    def _ingest_rx_file(self, name: str) -> None:
        src = Path(name)
        if not src.is_file():
            candidate = self._gallery.received_dir() / Path(name).name
            if candidate.is_file():
                src = candidate
            else:
                self._event_bus.publish(
                    LogEvent(level="warning", message=f"HamDRM GetFileRX reported missing file: {name}")
                )
                return
        dest_dir = self._gallery.received_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        else:
            dest = src
        self._event_bus.publish(RxImageReadyEvent(path=str(dest)))
        entry = self._gallery.add_image(
            dest, callsign=effective_callsign(self._config), direction="rx"
        )
        self._event_bus.publish(GalleryUpdatedEvent(image_id=entry.id, path=str(dest)))
        self._event_bus.publish(LogEvent(level="info", message=f"HamDRM RX complete: {dest.name}"))

    def transmit_file(self, path: Path) -> None:
        lib = self._require_lib()
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        self._play_callsign_header()
        with self._lock:
            self._apply_tx_params()
            self._apply_paths()
            out_dev = self._audio_device_id("out")
            lib.SetAudDeviceOut(out_dev)
            if not self._threads_started:
                lib.StartThreadTX(out_dev)
                self._threads_started = True
            ok = lib.SetFileTX(
                encode_c_path(file_path.name),
                encode_c_path(file_path),
                1,
            )
            if not ok:
                raise RuntimeError(f"SetFileTX failed for {file_path}")
            lib.ControlTX(True)
            self._tx_active = True
            self._start_tx_poll()
        self._event_bus.publish(LogEvent(level="info", message=f"HamDRM TX started: {file_path.name}"))

    def _start_tx_poll(self) -> None:
        self._tx_poll_stop.set()
        prev = self._tx_poll_thread
        if prev and prev.is_alive():
            prev.join(timeout=1.0)
        self._tx_poll_stop.clear()
        self._tx_poll_thread = threading.Thread(
            target=self._poll_tx_loop,
            name="hamdrm-tx-poll",
            daemon=True,
        )
        self._tx_poll_thread.start()

    def _poll_tx_loop(self) -> None:
        while not self._tx_poll_stop.wait(0.25):
            if self._lib is None or not self._tx_active:
                break
            try:
                with self._lock:
                    if self._lib is None or not self._tx_active:
                        break
                    pic = c_int(0)
                    pct = c_int(0)
                    done = bool(self._lib.GetPercentTX(byref(pic), byref(pct)))
                    pic_v = int(pic.value)
                    pct_v = int(pct.value)
                self._event_bus.publish(
                    TransferProgressEvent(
                        pct=float(pct_v),
                        bytes_done=pic_v,
                        bytes_total=max(1, pic_v + (0 if done else 1)),
                    )
                )
                self._publish_sync_status()
                if done:
                    with self._lock:
                        try:
                            if self._lib is not None:
                                self._lib.ControlTX(False)
                        except OSError as exc:
                            logger.warning("ControlTX(False) after TX done failed: %s", exc)
                        self._tx_active = False
                    self._event_bus.publish(
                        LogEvent(level="info", message="HamDRM TX complete")
                    )
                    self._event_bus.publish(
                        TransferProgressEvent(pct=100.0, bytes_done=1, bytes_total=1)
                    )
                    break
            except Exception as exc:  # noqa: BLE001
                self._event_bus.publish(
                    LogEvent(level="error", message=f"HamDRM TX poll error: {exc}")
                )
                break

    def start_tune(self) -> None:
        """Play callsign WFTxt, 1 s gap, then 720/1466/1840 Hz three-tone (max 5 s)."""
        if self._tuning or self._wftxt_busy or self._tx_active:
            return
        self._require_lib()
        self._tune_stop.clear()
        self._tuning = True
        self._tune_thread = threading.Thread(
            target=self._run_tune_tone,
            name="hamdrm-tune",
            daemon=True,
        )
        self._tune_thread.start()
        emission = self._config.transfer.radio_emission.upper()
        self._event_bus.publish(
            LogEvent(
                level="info",
                message=(
                    f"HamDRM Tune started ({emission}) — callsign, 1 s gap, "
                    "then 720/1466/1840 Hz three-tone (max 5 s); press F8 again to stop"
                ),
            )
        )

    def stop_tune(self) -> None:
        self._tune_stop.set()
        self._wftxt_stop.set()
        thread = self._tune_thread
        self._tune_thread = None
        if thread and thread.is_alive():
            thread.join(timeout=8.0)
        self._tuning = False

    def _run_tune_tone(self) -> None:
        try:
            self._set_ui_state(SessionState.TUNING)
            self._ptt_on()
            self._play_callsign_header(stop_event=self._tune_stop)
            if self._tune_stop.is_set():
                self._event_bus.publish(LogEvent(level="warning", message="HamDRM Tune aborted"))
                return

            # EasyPal tune.wav / green markers: 720 + 1466 + 1840 Hz, ≤5 s.
            out_rate = int(self._config.audio.sample_rate)
            max_s = min(5.0, float(self._config.transfer.tune_max_seconds))
            tune_pcm = load_tune_pcm(out_rate, duration_s=max_s)
            self._event_bus.publish(
                LogEvent(
                    level="info",
                    message=f"Playing Tune three-tone 720/1466/1840 Hz ({max_s:.0f} s)",
                )
            )
            self._play_pcm_on_air(
                tune_pcm,
                stop_event=self._tune_stop,
                ui_state=SessionState.TUNING,
                pcm_sample_rate=out_rate,
            )
            if self._tune_stop.is_set():
                self._event_bus.publish(LogEvent(level="warning", message="HamDRM Tune aborted"))
            else:
                self._event_bus.publish(LogEvent(level="info", message="HamDRM Tune finished"))
        except Exception as exc:  # noqa: BLE001
            self._event_bus.publish(LogEvent(level="error", message=f"HamDRM Tune failed: {exc}"))
        finally:
            self._ptt_off()
            self._tuning = False
            self._set_ui_state(SessionState.IDLE)

    def abort(self) -> None:
        self.stop_tune()
        self._wftxt_stop.set()
        self._tx_poll_stop.set()
        if not self.is_available() or self._lib is None:
            return
        with self._lock:
            try:
                self._lib.ControlTX(False)
                self._lib.ControlRX(False)
            except OSError as exc:
                logger.warning("HamDRM abort control failed: %s", exc)
            self._tx_active = False
            self._rx_active = False
            self._rx_paused_for_pcm = False
            self._wftxt_busy = False
            self._poll_stop.set()
        self._event_bus.publish(LogEvent(level="warning", message="HamDRM transfer aborted"))
        self._set_ui_state(SessionState.IDLE)

    def shutdown(self) -> None:
        """Stop RX/TX and release DLL worker threads (call on app exit)."""
        self.abort()
        self.stop_rx()
        if self._lib is not None and self._threads_started:
            try:
                self._lib.StopThreads()
            except OSError as exc:
                logger.warning("StopThreads failed: %s", exc)
            self._threads_started = False

    def get_spectrum(self) -> list[float]:
        lib = self._require_lib()
        with self._lock:
            buf = (c_float * SPECTRUM_BINS)()
            n = int(lib.GetSpectrum(buf))
            if n <= 0:
                return []
            count = min(n, SPECTRUM_BINS)
            values = [float(buf[i]) for i in range(count)]
        return linear_spectrum_to_db(values)

    def get_sync_state(self) -> SyncState:
        lib = self._require_lib()
        with self._lock:
            states = (c_int * _STATE_LEN)()
            lib.GetState(states)
            # DLL returns 10 * SNR_dB (EasyPal convention).
            snr_raw = float(lib.GetSNR())
            snr_db = snr_raw / 10.0
            level = lib.GetLevel()
            dc = lib.GetDCFreq()

            call_buf = create_string_buffer(16)
            callsign = ""
            if lib.GetCall(call_buf):
                callsign = call_buf.value.decode("ascii", errors="replace").strip("\x00 ")

            mode_b = c_char()
            spec_b = c_char()
            prot_b = c_char()
            qam_b = c_char()
            intl_b = c_char()
            mode = ""
            if lib.GetParams(byref(mode_b), byref(spec_b), byref(prot_b), byref(qam_b), byref(intl_b)):
                m = ord(mode_b.value) if mode_b.value else 0
                mode = _MODE_LABELS.get(m, str(m))
                q = ord(qam_b.value) if qam_b.value else 0
                s = ord(spec_b.value) if spec_b.value else 0
                p = ord(prot_b.value) if prot_b.value else 0
                i = ord(intl_b.value) if intl_b.value else 0
                mode = (
                    f"{mode} {_SPECOCC_LABELS.get(s, s)} "
                    f"QAM{_QAM_LABELS.get(q, q)} {_MSCPROT_LABELS.get(p, p)} "
                    f"{_INTERLEAVE_LABELS.get(i, i)}"
                )

            return SyncState(
                io=bool(states[_STATE_IO]),
                time=bool(states[_STATE_TIME]),
                frame=bool(states[_STATE_FRAME]),
                fac=bool(states[_STATE_FAC]),
                msc=bool(states[_STATE_MSC]),
                snr_db=snr_db,
                level=int(level),
                dc_freq=int(dc),
                callsign=callsign,
                mode=mode,
            )
