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
from easypal_next.modem.tx_image import prepare_hamdrm_tx_file
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
        self._rx_thread_started = False
        self._tx_thread_started = False
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._seen_rx: set[str] = set()
        self._lock = threading.RLock()
        self._tuning = False
        self._tune_stop = threading.Event()
        self._tune_thread: threading.Thread | None = None
        self._tx_active = False
        self._tx_busy = False
        self._tx_abort = threading.Event()
        self._tx_poll_stop = threading.Event()
        self._tx_poll_thread: threading.Thread | None = None
        self._file_tx_thread: threading.Thread | None = None
        self._wftxt_busy = False
        self._wftxt_stop = threading.Event()
        self._wftxt_thread: threading.Thread | None = None
        self._tx_pic_estimate = 2
        self._tx_progress_pct: int | None = None
        self._tx_progress_seg: int | None = None
        self._tx_deadline = 0.0
        self._tx_gallery_path: Path | None = None

    @property
    def engine_name(self) -> str:
        return "hamdrm"

    @property
    def is_tuning(self) -> bool:
        return self._tuning

    @property
    def is_tx_busy(self) -> bool:
        return self._tx_busy or self._tx_active

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
        qam = int(modem.hamdrm_qam)
        mode = str(modem.hamdrm_mode).upper()
        mscprot = str(modem.hamdrm_mscprot).lower()
        lead_in = int(modem.hamdrm_start_delay)
        lib.SetCall(encode_callsign(effective_callsign(self._config)))
        lib.SetParams(
            mode_constant(mode),
            specocc_constant(modem.hamdrm_specocc),
            mscprot_constant(mscprot),
            qam_constant(qam),  # type: ignore[arg-type]
            interleave_constant(modem.hamdrm_interleave),
        )
        lib.SetDCFreq(int(modem.hamdrm_dc_freq))
        lib.SetStartDelay(lead_in)
        # MOT lead-in adds a full-file leader object when lead_in >= 1.
        self._tx_pic_estimate = 2 if lead_in >= 1 else 1
        self._event_bus.publish(
            LogEvent(
                level="info",
                message=(
                    f"HamDRM TX profile: {mode}/{modem.hamdrm_specocc}/"
                    f"QAM{qam}/{mscprot}/{modem.hamdrm_interleave} "
                    f"lead-in={lead_in}"
                ),
            )
        )

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

    def _drm_callsign_ok(self, call: str) -> bool:
        """HamDRM ControlTX requires a letter and a digit (see callisok())."""
        has_alpha = any("A" <= ch <= "Z" for ch in call.upper())
        has_digit = any(ch.isdigit() for ch in call)
        return has_alpha and has_digit

    def _ensure_rx_thread(self, in_dev: int) -> None:
        lib = self._require_lib()
        if self._rx_thread_started:
            return
        lib.SetAudDeviceIn(in_dev)
        lib.StartThreadRX(in_dev)
        self._rx_thread_started = True

    def _ensure_tx_thread(self, out_dev: int) -> None:
        """Start the WinMM TX worker once — required before ControlTX produces audio."""
        lib = self._require_lib()
        if self._tx_thread_started:
            return
        lib.SetAudDeviceOut(out_dev)
        lib.StartThreadTX(out_dev)
        self._tx_thread_started = True
        self._event_bus.publish(
            LogEvent(level="info", message=f"HamDRM TX thread started (WinMM out={out_dev})")
        )

    def _set_ui_state(self, state: SessionState) -> None:
        self._event_bus.publish(SessionStateChangedEvent(state=state))

    def _pcm_sample_rate(self) -> int:
        return int(self._config.waterfall.sample_rate or self._config.audio.sample_rate)

    def _pause_rx_for_pcm(self) -> None:
        """Release WinMM capture so PortAudio can play WFTxt / Tune safely."""
        # Flag first so the GUI spectrum timer skips DLL calls mid-flight.
        # Do NOT StopThreads here — that has been segfaulting the x64 DLL mid-RX.
        self._rx_paused_for_pcm = True
        time.sleep(0.12)
        with self._lock:
            if self._rx_active and self._lib is not None:
                try:
                    self._lib.ControlRX(False)
                except OSError as exc:
                    logger.warning("Pause RX for PCM failed: %s", exc)
        time.sleep(0.2)

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
        paint_rate = int(self._config.waterfall.sample_rate or 25000)
        dur = len(pcm) / float(paint_rate) if paint_rate else 0.0
        self._event_bus.publish(
            LogEvent(level="info", message=f"Callsign WFTxt duration {dur:.1f} s")
        )
        self._play_pcm_on_air(pcm, stop_event=stop_event)
        if stop_event is None or not stop_event.is_set():
            self._header_gap(stop_event)

    def transmit_waterfall_text(self, message: str) -> None:
        """Play SpectrumPainter WFTxt PCM on the sound card (not via hamdrm.dll)."""
        text = (message or "").strip()
        if not text:
            raise ValueError("WFTxt message is empty")
        if self._tuning or self._tx_busy or self._tx_active or self._wftxt_busy:
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
            # EasyPal starts both workers at launch; TX must exist before ControlTX.
            self._ensure_rx_thread(in_dev)
            self._ensure_tx_thread(out_dev)
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
        if self._rx_paused_for_pcm or self._tuning or self._wftxt_busy or self._tx_busy or not self._rx_active:
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

    def _publish_sync_status(
        self,
        *,
        percent_tx: int | None = None,
        seg_pos: int | None = None,
    ) -> None:
        """Publish sync LEDs / TX %.

        Never call ``GetPercentTX`` here during file TX — that API has a
        destructive debounce counter. A second call per poll tick consumes the
        ``TRUE`` completion result and the MOT slideshow loops forever.
        """
        try:
            state = self.get_sync_state()
            cached_pct = percent_tx
            cached_seg = seg_pos
            if cached_pct is None:
                cached_pct = getattr(self, "_tx_progress_pct", None)
            if cached_seg is None:
                cached_seg = getattr(self, "_tx_progress_seg", None)
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
                    percent_tx=cached_pct,
                    seg_pos=cached_seg,
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
                            if self._ingest_rx_file(name):
                                self._seen_rx.add(name)
            except Exception as exc:  # noqa: BLE001 — keep poll alive
                self._event_bus.publish(
                    LogEvent(level="error", message=f"HamDRM RX poll error: {exc}")
                )

    def _ingest_rx_file(self, name: str) -> bool:
        """Copy RX file into gallery. Returns True only after a successful add."""
        src = Path(name)
        if not src.is_file():
            candidate = self._gallery.received_dir() / Path(name).name
            if candidate.is_file():
                src = candidate
            else:
                self._event_bus.publish(
                    LogEvent(
                        level="warning",
                        message=f"HamDRM GetFileRX reported missing file: {name}",
                    )
                )
                return False
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
        return True

    def transmit_file(self, path: Path) -> None:
        lib = self._require_lib()
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        if self._tx_busy or self._tx_active or self._tuning or self._wftxt_busy:
            raise RuntimeError("Transfer already in progress")

        call = effective_callsign(self._config)
        if not self._drm_callsign_ok(call):
            raise RuntimeError(
                f"Callsign '{call}' is not valid for HamDRM TX "
                "(need at least one letter and one digit, e.g. N0CALL / M0VUB)."
            )

        self._tx_abort.clear()
        self._tx_busy = True
        self._file_tx_thread = threading.Thread(
            target=self._run_file_tx,
            args=(file_path,),
            name="hamdrm-file-tx",
            daemon=True,
        )
        self._file_tx_thread.start()

    def _run_file_tx(self, file_path: Path) -> None:
        """Callsign header then DRM file TX; honour ``_tx_abort`` throughout."""
        lib = self._require_lib()
        aborted = False
        try:
            tx_path = prepare_hamdrm_tx_file(file_path)
            self._tx_gallery_path = tx_path
            src_kb = file_path.stat().st_size / 1024.0
            tx_kb = tx_path.stat().st_size / 1024.0
            # Handbook MSC rates (Mode B/2.5/norm/16 ≈ 2.3 kbps).
            qam = int(self._config.modem.hamdrm_qam)
            rough_bps = 3500.0 if qam >= 64 else 2300.0
            eta_min = max(0.2, (tx_kb * 1024.0 * 8.0) / rough_bps / 60.0)
            self._event_bus.publish(
                LogEvent(
                    level="info",
                    message=(
                        f"TX payload {tx_path.name}: {tx_kb:.1f} KB"
                        + (
                            f" (from {file_path.name} {src_kb:.1f} KB)"
                            if tx_path != file_path
                            else ""
                        )
                        + f" — payload ETA ~{eta_min:.1f} min (+ lead-in)"
                    ),
                )
            )

            # Skip PortAudio callsign WFTxt on HamDRM file TX — opening the sound
            # card beside WinMM has been hard-crashing the x64 DLL. FAC still carries
            # the callsign via SetCall.
            self._set_ui_state(SessionState.TX_ACTIVE)
            self._ptt_on()
            if self._should_play_callsign_header():
                self._event_bus.publish(
                    LogEvent(
                        level="info",
                        message="Skipping WFTxt callsign header for HamDRM file TX (FAC ID only)",
                    )
                )
            with self._lock:
                if self._tx_abort.is_set():
                    aborted = True
                    return
                self._apply_tx_params()
                self._apply_paths()
                out_dev = self._audio_device_id("out")
                in_dev = self._audio_device_id("in")
                lib.SetAudDeviceOut(out_dev)
                self._ensure_rx_thread(in_dev)
                self._ensure_tx_thread(out_dev)
                if self._rx_active:
                    try:
                        lib.ControlRX(False)
                    except OSError as exc:
                        logger.warning("ControlRX(False) before TX failed: %s", exc)
                    self._rx_paused_for_pcm = True
                ok = lib.SetFileTX(
                    encode_c_path(tx_path.name),
                    encode_c_path(tx_path),
                    1,
                )
                if not ok:
                    raise RuntimeError(f"SetFileTX failed for {tx_path}")
                lib.ControlTX(True)
                self._tx_active = True
                self._tx_progress_pct = 0
                self._tx_progress_seg = 0
                # Watchdog: native slideshow loops forever until ControlTX(False).
                # ~2 MOT objects × payload; FM/64 ≈ 4.5 kbps, keep a generous ceiling.
                rough_bps = 3500.0 if int(self._config.modem.hamdrm_qam) >= 64 else 2000.0
                pics = max(1, int(self._tx_pic_estimate))
                air_s = max(45.0, (tx_kb * 1024.0 * 8.0 * pics) / rough_bps * 2.5)
                self._tx_deadline = time.monotonic() + air_s
                # Segment count for ETA (Mode B ≈ 0.4 s/frame ballpark).
                tot = c_int(0)
                act = c_int(0)
                try:
                    lib.GetSegPosTX(byref(tot), byref(act))
                except Exception:  # noqa: BLE001
                    tot.value = 0
                segs = int(tot.value)
                self._event_bus.publish(
                    LogEvent(
                        level="info",
                        message=(
                            f"HamDRM TX armed: ~{pics} MOT object(s), "
                            f"seg≈{segs or '?'}/obj, watchdog {air_s / 60.0:.1f} min"
                        ),
                    )
                )
                self._start_tx_poll()
            self._event_bus.publish(
                LogEvent(level="info", message=f"HamDRM TX started: {tx_path.name}")
            )
            total_units = max(1, segs) * max(1, int(self._tx_pic_estimate))
            self._event_bus.publish(
                TransferProgressEvent(pct=0.0, bytes_done=0, bytes_total=total_units)
            )
            # Wait until poll finishes, abort, or watchdog.
            while self._tx_active and not self._tx_abort.is_set():
                if self._tx_deadline and time.monotonic() >= self._tx_deadline:
                    self._event_bus.publish(
                        LogEvent(
                            level="error",
                            message=(
                                "HamDRM TX watchdog — GetPercentTX never completed; "
                                "forcing ControlTX off (slideshow was looping)"
                            ),
                        )
                    )
                    aborted = True
                    break
                time.sleep(0.1)
            if self._tx_abort.is_set() and self._tx_active:
                aborted = True
        except Exception as exc:  # noqa: BLE001
            self._event_bus.publish(
                LogEvent(level="error", message=f"HamDRM TX failed: {exc}")
            )
            aborted = True
        finally:
            self._stop_file_tx(aborted=aborted)

    def _stop_tx_poll(self) -> None:
        self._tx_poll_stop.set()
        thread = self._tx_poll_thread
        self._tx_poll_thread = None
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _clear_transfer_progress(self) -> None:
        self._event_bus.publish(
            TransferProgressEvent(pct=0.0, bytes_done=0, bytes_total=0)
        )

    def _stop_file_tx(self, *, aborted: bool) -> None:
        """Idempotent end of a file TX (complete, error, or Abort)."""
        with self._lock:
            if not self._tx_busy and not self._tx_active:
                return
            if self._lib is not None:
                try:
                    self._lib.ControlTX(False)
                except OSError as exc:
                    logger.warning("ControlTX(False) failed: %s", exc)
            self._tx_active = False
            self._tx_busy = False
        self._stop_tx_poll()
        self._ptt_off()
        # Resume always-on RX if we paused it for TX (do not tear RX down).
        if self._rx_paused_for_pcm:
            self._resume_rx_after_pcm()
        elif self._rx_active and self._lib is not None:
            try:
                with self._lock:
                    if self._lib is not None and self._rx_active and not self._rx_paused_for_pcm:
                        self._lib.ControlRX(True)
            except OSError as exc:
                logger.warning("ControlRX(True) after TX failed: %s", exc)
        self._clear_transfer_progress()
        self._set_ui_state(SessionState.IDLE)
        gallery_path = self._tx_gallery_path
        self._tx_gallery_path = None
        if aborted:
            self._event_bus.publish(
                LogEvent(level="warning", message="HamDRM TX aborted — ready for next file")
            )
        else:
            self._event_bus.publish(LogEvent(level="info", message="HamDRM TX complete"))
            if gallery_path is not None and gallery_path.is_file():
                try:
                    entry = self._gallery.add_image(
                        gallery_path,
                        callsign=effective_callsign(self._config),
                        direction="tx",
                    )
                    self._event_bus.publish(
                        GalleryUpdatedEvent(image_id=entry.id, path=str(gallery_path))
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Gallery TX entry failed: %s", exc)

    def _start_tx_poll(self) -> None:
        self._stop_tx_poll()
        self._tx_poll_stop.clear()
        self._tx_poll_thread = threading.Thread(
            target=self._poll_tx_loop,
            name="hamdrm-tx-poll",
            daemon=True,
        )
        self._tx_poll_thread.start()

    def _poll_tx_loop(self) -> None:
        """Poll HamDRM TX once per tick — single GetPercentTX call (see sync note)."""
        last_log = 0.0
        peak_pct = 0.0
        # Lead-in>=1 → leader MOT object + payload (see MOTSlideShow.cpp).
        pic_total = max(1, int(getattr(self, "_tx_pic_estimate", 2)))
        while not self._tx_poll_stop.wait(0.25):
            if self._lib is None or not self._tx_active or self._tx_abort.is_set():
                break
            try:
                with self._lock:
                    if self._lib is None or not self._tx_active:
                        break
                    # ONLY call GetPercentTX here — never from sync publish during TX.
                    pic = c_int(0)
                    pct = c_int(0)
                    done = bool(self._lib.GetPercentTX(byref(pic), byref(pct)))
                    tot = c_int(0)
                    act = c_int(0)
                    try:
                        self._lib.GetSegPosTX(byref(tot), byref(act))
                    except Exception:  # noqa: BLE001
                        tot.value = 0
                        act.value = 0
                    pic_done = max(0, int(pic.value))
                    obj_pct = max(0, min(100, int(pct.value)))
                    seg_tot = max(0, int(tot.value))
                    seg_act = max(0, int(act.value))
                if self._tx_abort.is_set() or not self._tx_active:
                    break

                # Grow estimate if DLL reports more completed objects than expected.
                pic_total = max(pic_total, pic_done + (0 if done else 1), 1)
                if seg_tot > 0:
                    # Full-transfer % across all MOT objects (not per-segment reset).
                    overall = (pic_done * seg_tot + min(seg_act, seg_tot)) / float(
                        pic_total * seg_tot
                    )
                    pct_v = int(min(100, round(100.0 * overall)))
                    done_n = pic_done * seg_tot + seg_act
                    total_n = pic_total * seg_tot
                else:
                    overall = (pic_done * 100 + obj_pct) / float(pic_total * 100)
                    pct_v = int(min(100, round(100.0 * overall)))
                    done_n = pic_done
                    total_n = pic_total
                if done:
                    pct_v = 100
                peak_pct = max(peak_pct, float(pct_v))
                pct_v = int(peak_pct)
                self._tx_progress_pct = pct_v
                self._tx_progress_seg = seg_act

                self._event_bus.publish(
                    TransferProgressEvent(
                        pct=float(pct_v),
                        bytes_done=done_n,
                        bytes_total=total_n,
                    )
                )
                self._publish_sync_status(percent_tx=pct_v, seg_pos=seg_act)

                now = time.monotonic()
                if now - last_log >= 5.0:
                    last_log = now
                    self._event_bus.publish(
                        LogEvent(
                            level="info",
                            message=(
                                f"HamDRM TX progress {pct_v}% "
                                f"(pics {pic_done}/{pic_total}, "
                                f"seg {seg_act}/{seg_tot}"
                                f"{', complete' if done else ''})"
                            ),
                        )
                    )

                if done:
                    self._event_bus.publish(
                        LogEvent(
                            level="info",
                            message="HamDRM GetPercentTX complete — stopping TX",
                        )
                    )
                    with self._lock:
                        self._tx_active = False
                    break
            except Exception as exc:  # noqa: BLE001
                self._event_bus.publish(
                    LogEvent(level="error", message=f"HamDRM TX poll error: {exc}")
                )
                with self._lock:
                    self._tx_active = False
                break

    def start_tune(self) -> None:
        """Play callsign WFTxt, 1 s gap, then 720/1466/1840 Hz three-tone (max 5 s)."""
        if self._tuning or self._wftxt_busy or self._tx_busy or self._tx_active:
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
        """Stop Tune / WFTxt / file TX cleanly without tearing down always-on RX."""
        self.stop_tune()
        self._wftxt_stop.set()
        self._tx_abort.set()
        self._tx_poll_stop.set()

        with self._lock:
            if self._lib is not None:
                try:
                    self._lib.ControlTX(False)
                except OSError as exc:
                    logger.warning("HamDRM abort ControlTX failed: %s", exc)

        file_thread = self._file_tx_thread
        if file_thread and file_thread.is_alive() and file_thread is not threading.current_thread():
            file_thread.join(timeout=8.0)
        self._file_tx_thread = None

        wftxt_thread = self._wftxt_thread
        if wftxt_thread and wftxt_thread.is_alive() and wftxt_thread is not threading.current_thread():
            wftxt_thread.join(timeout=5.0)

        # Finish any leftover TX state (no-op if worker already cleaned up).
        self._stop_file_tx(aborted=True)
        self._wftxt_busy = False
        self._clear_transfer_progress()
        self._set_ui_state(SessionState.IDLE)
        # Keep always-on RX alive — never set _poll_stop / _rx_active here.
        if self._rx_active and self._lib is not None and not self._rx_paused_for_pcm:
            try:
                with self._lock:
                    if self._lib is not None and self._rx_active:
                        self._lib.ControlRX(True)
            except OSError as exc:
                logger.warning("HamDRM abort ControlRX(True) failed: %s", exc)
        self._event_bus.publish(
            LogEvent(level="warning", message="HamDRM abort complete — idle")
        )

    def shutdown(self) -> None:
        """Stop RX/TX and release DLL worker threads (call on app exit)."""
        self.abort()
        self.stop_rx()
        if self._lib is not None and (self._rx_thread_started or self._tx_thread_started):
            try:
                self._lib.StopThreads()
            except OSError as exc:
                logger.warning("StopThreads failed: %s", exc)
            self._rx_thread_started = False
            self._tx_thread_started = False

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
