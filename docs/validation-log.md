# EasyPal-Next Validation Log

Record end-to-end validation before any public release. Update this file after each shack or loopback session.

## Environment

| Field | Value |
|-------|-------|
| Date | 2026-07-10 |
| EasyPal-Next commit | (uncommitted — Phase 4 work in progress) |
| Python | 3.12.10 (`.venv`) |
| OS | Windows 10/11 |
| libcodec2 source | MSYS2 UCRT64 via `scripts/fetch-libcodec2.py` |
| Redist DLLs | `libcodec2.dll`, `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll` |

## Automated checks

| Check | Result | Notes |
|-------|--------|-------|
| `python scripts/verify-codec2.py` | **PASS** | DATAC3 @ 8000 Hz, 126-byte payload |
| `python scripts/loopback-transfer.py` | **PASS** | SHA256 match (`loopback.txt`) |
| `pytest` (full suite) | **PASS** | 20 tests, 0 integration skips |
| `pytest tests/integration` | **PASS** | modem + transfer loopback (waterfall enabled in integration test) |

## Desktop UI loopback (manual)

| Step | Result | Notes |
|------|--------|-------|
| Launch `python -m easypal_next` | _pending_ | |
| LoadPic → small JPEG/bin → Transmit | _pending_ | Default `transfer.loopback_mode: true` |
| RX pane + gallery update | _pending_ | |

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

- **Modem framer padding:** RX modem frames are zero-padded to 126 bytes; `ModemFramer.feed()` now trims to `(total - offset)` so EPNX packets reassemble correctly.
- **Gallery non-images:** `GalleryStore.add_image()` now uses a placeholder thumbnail for non-image received files (`.txt`, `.bin`).
- **Inno Setup script:** `SetupIcon` → `SetupIconFile` in `easypal-next.iss`.

## Release gate

Public release (tag `v0.2.0`, GitHub Release, README download link) remains **deferred** until on-air validation and installer smoke test are complete.
