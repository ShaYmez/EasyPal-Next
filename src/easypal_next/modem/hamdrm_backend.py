"""HamDRM transfer backend wrapping run.dll / hamdrm.dll via ctypes."""

from __future__ import annotations

import logging
import shutil
import threading
from ctypes import byref, c_char, c_float, c_int, create_string_buffer
from pathlib import Path

from easypal_next.app.paths import user_data_dir
from easypal_next.config.schema import AppConfig
from easypal_next.core.events import (
    EventBus,
    GalleryUpdatedEvent,
    LogEvent,
    RxImageReadyEvent,
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

logger = logging.getLogger(__name__)

# GetState layout used by EasyPal / WinDRM UIs: IO, Time, Frame, FAC, MSC
_STATE_IO = 0
_STATE_TIME = 1
_STATE_FRAME = 2
_STATE_FAC = 3
_STATE_MSC = 4
_STATE_LEN = 8

_POLL_INTERVAL_S = 0.4

_MODE_LABELS = {0: "A", 1: "B", 2: "E"}
_SPECOCC_LABELS = {0: "2.3", 1: "2.5"}
_QAM_LABELS = {0: "4", 1: "16", 2: "64"}
_INTERLEAVE_LABELS = {0: "short", 1: "long"}
_MSCPROT_LABELS = {0: "normal", 1: "low"}


class HamDrmBackend(TransferBackend):
    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        gallery: GalleryStore,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._gallery = gallery
        self._lib = None
        self._dll_path: Path | None = None
        self._available: bool | None = None
        self._unavailable_reason: str | None = None
        self._rx_active = False
        self._threads_started = False
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._seen_rx: set[str] = set()
        self._lock = threading.RLock()

    @property
    def engine_name(self) -> str:
        return "hamdrm"

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
        lib.SetCall(encode_callsign(self._config.callsign))
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

    def _audio_device_id(self, which: str) -> int:
        cfg = self._config.audio
        if which == "in":
            return int(cfg.input_device) if cfg.input_device is not None else 0
        return int(cfg.output_device) if cfg.output_device is not None else 0

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

    def _poll_rx_loop(self) -> None:
        buf = create_string_buffer(260)
        while not self._poll_stop.wait(_POLL_INTERVAL_S):
            try:
                lib = self._lib
                if lib is None:
                    continue
                if not lib.GetFileRX(buf):
                    continue
                name = buf.value.decode("mbcs", errors="replace").strip()
                if not name or name in self._seen_rx:
                    continue
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
        entry = self._gallery.add_image(dest, callsign=self._config.callsign, direction="rx")
        self._event_bus.publish(GalleryUpdatedEvent(image_id=entry.id, path=str(dest)))
        self._event_bus.publish(LogEvent(level="info", message=f"HamDRM RX complete: {dest.name}"))

    def transmit_file(self, path: Path) -> None:
        lib = self._require_lib()
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
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
        self._event_bus.publish(LogEvent(level="info", message=f"HamDRM TX started: {file_path.name}"))

    def start_tune(self) -> None:
        raise HamDrmUnavailable(
            "HamDRM tune is not implemented in this scaffolding — use FreeDV tune or EasyPal Tune."
        )

    def stop_tune(self) -> None:
        return

    def abort(self) -> None:
        if not self.is_available() or self._lib is None:
            return
        with self._lock:
            try:
                self._lib.ControlTX(False)
                self._lib.ControlRX(False)
            except OSError as exc:
                logger.warning("HamDRM abort control failed: %s", exc)
            self._rx_active = False
            self._poll_stop.set()
        self._event_bus.publish(LogEvent(level="warning", message="HamDRM transfer aborted"))

    def get_spectrum(self) -> list[float]:
        lib = self._require_lib()
        buf = (c_float * SPECTRUM_BINS)()
        lib.GetSpectrum(buf)
        return [float(buf[i]) for i in range(SPECTRUM_BINS)]

    def get_sync_state(self) -> SyncState:
        lib = self._require_lib()
        states = (c_int * _STATE_LEN)()
        lib.GetState(states)
        snr = lib.GetSNR()
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
                f"{mode} QAM{_QAM_LABELS.get(q, q)} "
                f"{_SPECOCC_LABELS.get(s, s)}kHz {_MSCPROT_LABELS.get(p, p)} "
                f"{_INTERLEAVE_LABELS.get(i, i)}"
            )

        return SyncState(
            io=bool(states[_STATE_IO]),
            time=bool(states[_STATE_TIME]),
            frame=bool(states[_STATE_FRAME]),
            fac=bool(states[_STATE_FAC]),
            msc=bool(states[_STATE_MSC]),
            snr_db=float(snr),
            level=int(level),
            dc_freq=int(dc),
            callsign=callsign,
            mode=mode,
        )
