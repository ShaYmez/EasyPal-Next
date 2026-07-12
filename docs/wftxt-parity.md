# WFTxt / Tune parity dig (EasyPal vs EasyPal-Next)

Captured from this machine’s EasyPal install (`%APPDATA%\EasyPal\programwavfiles\`) and Next’s SpectrumPainter encoder. Goal: match on-air sound and keep-rolling waterfall paint without rewriting the Qt UI.

## EasyPal golden cues

| File | Rate | Duration | Notes |
|------|------|----------|-------|
| `bsr.wav`, `fileok.wav`, … | **25000 Hz**, 8-bit mono | **3.318 s** (82944 frames) | WFTxt-style paint; energy period ≈ **40.96 ms**/column |
| `tune.wav` | **11025 Hz**, 16-bit mono | **6.0 s** | Peaks at **720 / 1466 / 1840 Hz** (green markers) |

Active paint band in cue WAVs spans roughly **150–2800 Hz**. Peak level after u8→i16 conversion ≈ **9–11k** (not full-scale).

## Next (pre-calibration) vs goldens

| Stimulus | Duration | Peak (i16) | Gap |
|----------|----------|------------|-----|
| EasyPal `bsr.wav` | 3.32 s | ~9.5k | — |
| Next `TEST` / `M0VUB` (`min_columns=80`, 41 ms) | 3.28 s | ~21k | Duration OK; **too hot** |
| Next paint grid | `PAINT_HZ_PER_PIXEL=18` | — | EasyPal display ~**11.63 Hz/px** (coarser → fewer, brighter tones) |
| Next Tune synth | 5 s @ device rate | — | Freqs match; prefer real `tune.wav` when present |

## Root causes of “sounds different / waterfall freezes”

1. **Louder / harsher paint** — peak normalize ~0.65 FS vs EasyPal ~0.3 FS.
2. **Coarser freq grid** — 18 Hz/px vs ~12 Hz/px → different timbre and glyph density.
3. **PortAudio resample 25 kHz → 48 kHz** beside HamDRM WinMM — timbre shift + crash risk.
4. **RX spectrum paused** during WFTxt; display must be driven from **TX PCM tap** or the cascade freezes.

## Calibration applied in code

- Paint grid ≈ **12 Hz/pixel**; `freq_max_hz` **2700**.
- Peak normalize ≈ **0.35** (EasyPal cue loudness).
- Short body text: **tile ink columns** to ~3.2 s (cue length), not silent `min_columns` padding alone.
- HamDRM play: **WinMM `winsound`** at native encode rate (no PortAudio on the HamDRM device).
- Waterfall: feed TX tap from the PCM being played so glyphs scroll while RX `GetSpectrum` is paused.
- Tune: load EasyPal/`resources` `tune.wav` when available; same WinMM play path.

## Operator note

Close stock EasyPal while testing Next on the same sound device. If WFTxt still fights the card, set a dedicated output (virtual cable) later — do not re-enable PortAudio on the HamDRM device.
