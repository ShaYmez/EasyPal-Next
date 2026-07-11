"""Modem factory."""

from __future__ import annotations

from dataclasses import dataclass

from easypal_next.app.paths import resolve_libcodec2
from easypal_next.config.schema import AppConfig, ModemConfig
from easypal_next.core.events import EventBus, LogEvent
from easypal_next.core.transfer_engine import TransferEngine
from easypal_next.modem.ctypes_backend import CtypesFreeDvModem
from easypal_next.modem.freedv_backend import FreeDvBackend
from easypal_next.modem.hamdrm_backend import HamDrmBackend
from easypal_next.modem.interface import ModemInterface
from easypal_next.modem.transfer_backend import TransferBackend
from easypal_next.network.gallery_store import GalleryStore


@dataclass
class TransferBackendSelection:
    backend: TransferBackend
    requested_engine: str
    active_engine: str
    hamdrm_fell_back: bool = False
    hamdrm_unavailable_reason: str | None = None


def create_modem(config: ModemConfig) -> ModemInterface:
    lib_path = resolve_libcodec2(config.libcodec2_path)
    return CtypesFreeDvModem(lib_path)


def create_transfer_backend(
    config: AppConfig,
    event_bus: EventBus,
    gallery: GalleryStore,
    transfer_engine: TransferEngine,
) -> TransferBackend:
    """Create the configured transfer backend.

    When ``modem.engine == \"hamdrm\"`` but the DLL cannot load (missing or wrong
    bitness), publishes a LogEvent warning and falls back to FreeDV for usability.
    """
    selection = create_transfer_backend_selection(config, event_bus, gallery, transfer_engine)
    return selection.backend


def create_transfer_backend_selection(
    config: AppConfig,
    event_bus: EventBus,
    gallery: GalleryStore,
    transfer_engine: TransferEngine,
) -> TransferBackendSelection:
    requested = config.modem.engine
    if requested == "hamdrm":
        hamdrm = HamDrmBackend(config, event_bus, gallery)
        if hamdrm.is_available():
            return TransferBackendSelection(
                backend=hamdrm,
                requested_engine="hamdrm",
                active_engine="hamdrm",
            )
        reason = hamdrm.unavailable_reason() or "HamDRM DLL unavailable"
        event_bus.publish(
            LogEvent(
                level="warning",
                message=(
                    f"HamDRM engine unavailable — falling back to FreeDV. {reason}"
                ),
            )
        )
        freedv = FreeDvBackend(config, transfer_engine, hamdrm_fell_back=True)
        return TransferBackendSelection(
            backend=freedv,
            requested_engine="hamdrm",
            active_engine="freedv",
            hamdrm_fell_back=True,
            hamdrm_unavailable_reason=reason,
        )

    return TransferBackendSelection(
        backend=FreeDvBackend(config, transfer_engine),
        requested_engine="freedv",
        active_engine="freedv",
    )
