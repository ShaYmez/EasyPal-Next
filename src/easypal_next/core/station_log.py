"""Station Log — append-only TX/RX event file + helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from easypal_next.app.paths import user_data_dir


@dataclass
class StationLogEntry:
    ts: str
    direction: str  # tx | rx | cw | note
    callsign: str
    path: str = ""
    detail: str = ""
    snr_db: float | None = None


def station_log_dir() -> Path:
    path = user_data_dir() / "station_log"
    path.mkdir(parents=True, exist_ok=True)
    return path


def station_log_path() -> Path:
    return station_log_dir() / "station_log.jsonl"


def append_station_log(
    *,
    direction: str,
    callsign: str,
    path: str = "",
    detail: str = "",
    snr_db: float | None = None,
) -> StationLogEntry:
    entry = StationLogEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        direction=direction,
        callsign=(callsign or "").strip().upper() or "N0CALL",
        path=path,
        detail=detail,
        snr_db=snr_db,
    )
    log = station_log_path()
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return entry


def read_station_log(*, limit: int = 500) -> list[StationLogEntry]:
    log = station_log_path()
    if not log.is_file():
        return []
    lines = log.read_text(encoding="utf-8").splitlines()
    entries: list[StationLogEntry] = []
    for line in lines[-max(1, limit) :]:
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            entries.append(
                StationLogEntry(
                    ts=str(raw.get("ts", "")),
                    direction=str(raw.get("direction", "")),
                    callsign=str(raw.get("callsign", "")),
                    path=str(raw.get("path", "")),
                    detail=str(raw.get("detail", "")),
                    snr_db=raw.get("snr_db"),
                )
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return entries
