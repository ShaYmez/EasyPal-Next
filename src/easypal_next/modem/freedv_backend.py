"""FreeDV transfer backend wrapping the existing TransferEngine."""

from __future__ import annotations

from pathlib import Path

from easypal_next.app.paths import resolve_libcodec2
from easypal_next.config.schema import AppConfig
from easypal_next.core.transfer_engine import TransferEngine
from easypal_next.modem.transfer_backend import SyncState, TransferBackend


class FreeDvBackend(TransferBackend):
    """Thin adapter so UI / factory can talk to TransferEngine via TransferBackend."""

    def __init__(
        self,
        config: AppConfig,
        transfer_engine: TransferEngine,
        *,
        hamdrm_fell_back: bool = False,
    ) -> None:
        self._config = config
        self._engine = transfer_engine
        self.hamdrm_fell_back = hamdrm_fell_back

    @property
    def engine_name(self) -> str:
        return "freedv"

    def is_available(self) -> bool:
        return resolve_libcodec2(self._config.modem.libcodec2_path) is not None

    def start_always_on_rx(self) -> None:
        # Always-on RX implies auto receive even if config previously had it off.
        self._config.transfer.auto_rx = True
        self._engine.start_auto_rx()

    def stop_rx(self) -> None:
        self._engine.abort()

    def transmit_file(self, path: Path) -> None:
        self._engine.start_tx(Path(path))

    def transmit_waterfall_text(self, message: str) -> None:
        self._engine.start_waterfall_tx(message)

    def start_tune(self) -> None:
        self._engine.start_tune()

    def stop_tune(self) -> None:
        self._engine.stop_tune()

    def abort(self) -> None:
        self._engine.abort()

    def get_spectrum(self) -> list[float]:
        # Spectrum already flows via EventBus / WaterfallTap.
        return []

    def get_sync_state(self) -> SyncState:
        state = self._engine.state
        listening = state.name in {"RX_LISTEN", "RX_ASSEMBLING"}
        return SyncState(
            io=listening,
            time=listening,
            frame=listening,
            fac=False,
            msc=False,
            snr_db=None,
            level=None,
            dc_freq=None,
            callsign=self._config.callsign,
            mode=self._config.modem.mode,
        )
