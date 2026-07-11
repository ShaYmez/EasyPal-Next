# On-Air Transfer Test Guide

EasyPal-Next Phase 3 validates error-corrected file transfer over a real audio path.

## Prerequisites

- `libcodec2.dll` at `packaging/windows/redist/libcodec2.dll`
- `python scripts/verify-codec2.py` exits 0
- `python scripts/loopback-transfer.py` exits 0 (modem + FEC path)
- Radio interface (SignaLink, Digirig, or similar) with VOX or PTT

## Configuration

Use **Settings** in the app (General, Audio, Radio, Waterfall tabs) or edit `%APPDATA%\EasyPal-Next\config.yaml`:

```yaml
transfer:
  loopback_mode: false
  tune_max_seconds: 30
  radio_emission: fm   # fm | am | ssb — Tune waterfall hints only

audio:
  input_device: <mic/input index>
  output_device: <radio/soundcard output index>
  sample_rate: 48000
  block_size: 1024

network:
  gallery_dir: C:\Users\You\EasyPal-Next\gallery
  received_dir: C:\Users\You\EasyPal-Next\received

radio:
  profile: vox          # vox | serial | cat
  pre_tx_delay_ms: 300
  post_tx_delay_ms: 200
  # serial: port, line (RTS/DTR), active_low, baud
  # cat: port, rig_model (3073 default), baud, ptt_method (rig/data)

waterfall:
  enabled: true
  tx_monitor: true
  begin_message: "<< EASYPAL >>"
```

**SignaLink / Digirig:** set audio input/output to the USB sound card; use **VOX** on the interface or **Serial PTT** / **Hamlib CAT** on the Radio tab (COM port dropdown with Refresh).

Set your callsign in **General** or config. Restart the app after changing loopback mode or gallery/received paths.

## Tune (audio alignment)

Before your first on-air transfer, use **Transfer → Tune** (toolbar **Tune**, **F8**) to loop the modem preamble through the sound card while PTT is active. The waterfall shows live spectrum so you can set drive, VOX threshold, or MIC gain without sending a file.

1. Set **Settings → General → Loopback mode** off; restart if you changed it.
2. **Settings → Transfer → Radio emission** to match how you operate:
   - **FM** — SignaLink / data VOX; typical VHF/UHF FM data
   - **AM** — low drive; avoid over-modulation on the carrier
   - **SSB / USB** — HF voice-style: USB, ~2.4 kHz filter, no compression
3. Set RF frequency and mode on the radio manually (EasyPal does not CAT-tune the dial in v1).
4. Press **Tune** (or **F8**). PTT keys; preamble audio loops until timeout (**Tune timeout**, default 30 s) or you press **Tune** again / **Abort**.
5. Adjust levels until the waterfall shows a clean DATAC3 tone band without clipping.

Tune is disabled in loopback mode (no sound card / PTT path).

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
- [ ] Live waterfall scrolls during loopback TX (Settings → Waterfall → tx_monitor)
- [ ] Send WFTxt toolbar sends text-only waterfall (no file)
- [ ] Tune (F8) loops preamble on-air; waterfall scrolls; auto-stops at timeout
- [ ] FM / AM / SSB emission setting matches your radio mode (Tune hints)
- [ ] PTT activates before audio (on-air mode)
- [ ] RX and TX entries show direction badges in gallery (desktop + LAN)
- [ ] SHA256 verified on received file

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No modem audio | `libcodec2.dll` path, audio output device |
| RX never completes | Both stations same modem mode (DATAC3), levels not clipping |
| Truncated file | Update to Phase 3+ (modem framer fixes packet size) |
| Waterfall garbled | Waterfall is resampled to modem rate automatically in Phase 3 |
