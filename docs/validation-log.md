# EasyPal-Next Validation Log

Record end-to-end validation before any public release. Update this file after each shack or loopback session.

## Environment

| Field | Value |
|-------|-------|
| Date | 2026-07-12 |
| EasyPal-Next commit | 221de1a + WFTxt cleanup (uncommitted) |
| Python | 3.12.10 (`.venv`) |
| OS | Windows 10/11 |
| libcodec2 source | MSYS2 UCRT64 via `scripts/fetch-libcodec2.py` |
| Redist DLLs | `libcodec2.dll`, `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll` |

## Automated checks

| Check | Result | Notes |
|-------|--------|-------|
| `python scripts/verify-codec2.py` | **PASS** | DATAC3 @ 8000 Hz, 126-byte payload |
| `python scripts/loopback-transfer.py` | **PASS** | SHA256 match (`loopback.txt`) |
| `pytest` (full suite) | **PASS** | 95 tests (incl. WFTxt parity, HamDRM WFTxt, integration loopback) |
| `pytest tests/integration` | **PASS** | modem + transfer loopback (waterfall enabled in integration test) |
| WFTxt parity unit tests | **PASS** | 12 Hz/px grid, 0.35 FS peak, stretch to ~3.2 s, slash_zeros, local `tune.wav` resolved |

## Desktop UI loopback (manual)

| Step | Result | Notes |
|------|--------|-------|
| Launch `python -m easypal_next` | _pending_ | Shared `app.qss` theme |
| Settings tabs (paths, COM, waterfall) | _pending_ | Gallery/received dirs, radio profile |
| LoadPic → small JPEG → Transmit | _pending_ | Real thumbnails (not blue placeholder) |
| TX + RX badges in gallery pane | _pending_ | Filter All / RX / TX |
| Waterfall scrolls during loopback TX | _pending_ | Option A live spectrum |
| Send WFTxt (text-only) | _pending_ | F7 / toolbar; encoder parity verified in unit tests — close stock EasyPal on same device |

## On-air transfer (manual)

| Field | Value |
|-------|-------|
| Hardware | _pending_ (SignaLink / Digirig / VB-Cable) |
| Loopback mode | disabled + app restart required |
| File | _pending_ (~50 KB JPEG recommended) |
| SHA256 match | _pending_ |
| LAN gallery (`:8765`) | _pending_ |

See [on-air-test.md](on-air-test.md) and [scripts/vbcable-loopback.py](../scripts/vbcable-loopback.py).

## Windows installer (local)

| Step | Result | Notes |
|------|--------|-------|
| `packaging/windows/build.ps1` (PyInstaller) | **PASS** | Bundle at `packaging/windows/dist/EasyPal-Next/`; all 4 codec2 DLLs in `_internal/` |
| Inno Setup installer (`iscc`) | **PASS** | `packaging/windows/output/EasyPal-Next-Setup-0.2.0.exe` (~53 MB) |
| Silent install smoke test | **PASS** | Installed to `EasyPal-Next-install-test/`; libcodec2 loads; app launches |

## Known issues / fixes this session

- **WFTxt stale code removed:** Deleted unused `decoder.py`, `wav_store.py`, `presets.py`; removed `WaterfallTextReceivedEvent` and unused `list_user_wave_*` helpers.
- **FreeDV/loopback WFTxt unified:** `TransferEngine` now uses `encode_waterfall_text` (stretch, slash_zeros, calibrated loudness) instead of raw `text_to_audio`.
- **WFTxt busy guard:** `main_window._send_wftxt` checks HamDRM `_wftxt_busy` / `_tx_busy` in addition to `transfer_engine.state`.
- **Modem framer padding:** RX modem frames are zero-padded to 126 bytes; `ModemFramer.feed()` now trims to `(total - offset)` so EPNX packets reassemble correctly.
- **Gallery non-images:** `GalleryStore.add_image()` now uses a placeholder thumbnail for non-image received files (`.txt`, `.bin`).
- **Inno Setup script:** `SetupIcon` → `SetupIconFile` in `easypal-next.iss`.

## Release gate

Public release (tag `v0.2.0`, GitHub Release, README download link) remains **deferred** until on-air validation and installer smoke test are complete.
