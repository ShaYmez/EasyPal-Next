# On-Air Transfer Test Guide

EasyPal-Next Phase 3 validates error-corrected file transfer over a real audio path.

## Prerequisites

- `libcodec2.dll` at `packaging/windows/redist/libcodec2.dll`
- `python scripts/verify-codec2.py` exits 0
- `python scripts/loopback-transfer.py` exits 0 (modem + FEC path)
- Radio interface (SignaLink, Digirig, or similar) with VOX or PTT

## Configuration

Edit `%APPDATA%\EasyPal-Next\config.yaml` or use **Settings** in the app:

```yaml
transfer:
  loopback_mode: false

audio:
  input_device: <mic/input index>
  output_device: <radio/soundcard output index>

radio:
  profile: vox
  pre_tx_delay_ms: 300
  post_tx_delay_ms: 200
```

Set your callsign in config or via Settings.

## Two-Station Test (recommended)

1. **Station A (TX):** LoadPic → select a small JPEG (~50 KB) → Transmit
2. **Station B (RX):** Receive before TX starts
3. Wait for TX progress to complete on A
4. Verify on B:
   - Desktop RX pane shows decoded image
   - LAN gallery at `http://<ip>:8765` updates
   - File SHA256 matches original

## Single-PC Test (VB-Audio Virtual Cable)

1. Install [VB-Cable](https://vb-audio.com/Cable/) or similar virtual audio device
2. Configure:
   - TX output → CABLE Input
   - RX input → CABLE Output
3. Run two app instances (or use `scripts/vbcable-loopback.py` for headless test)
4. Instance 1: Receive
5. Instance 2: Transmit test file

## Checklist

- [ ] `verify-codec2.py` passes
- [ ] `loopback-transfer.py` SHA256 match
- [ ] Waterfall header visible on spectrum (if enabled)
- [ ] PTT activates before audio (on-air mode)
- [ ] RX image appears in gallery
- [ ] SHA256 verified on received file

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No modem audio | `libcodec2.dll` path, audio output device |
| RX never completes | Both stations same modem mode (DATAC3), levels not clipping |
| Truncated file | Update to Phase 3+ (modem framer fixes packet size) |
| Waterfall garbled | Waterfall is resampled to modem rate automatically in Phase 3 |
