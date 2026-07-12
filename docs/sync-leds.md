# Sync LED honesty (EasyPal dig)

## EasyPal / hamdrm.dll semantics

`GetState(int *states)` copies `messtate[0..7]` from `PostWinMessage` (`native/hamdrm-dll/hamdrm.cpp`).

Message IDs (`GlobalDefinitions.h`):

| Index | ID | UI label |
|------:|----|----------|
| 1 | `MS_FAC_CRC` | FAC |
| 2 | `MS_MSC_CRC` | MSC |
| 3 | `MS_FRAME_SYNC` | Frame |
| 4 | `MS_TIME_SYNC` | Time |
| 5 | `MS_IOINTERFACE` | IO |

LED parameter values (same as EasyPal WinDRM lights):

| Value | Meaning |
|------:|---------|
| **0** | Green / OK |
| **1** | Yellow |
| **2** | Red / bad |
| **-1** | Never set / after `MS_RESET_ALL` |

## Bug that caused false greens

Next previously mapped IO/Time/Frame/FAC/MSC to indices **0–4** (wrong) and used `bool(state)`.

`messtate` starts as all **-1**. In Python `bool(-1)` is **True**, so every LED lit green on idle even with no DRM picture / no FAC lock.

## Fix

- Map LEDs to indices **1–5** as above.
- Green only when value **`== 0`**.
- SNR / decoded callsign / mode shown only when FAC is green; otherwise `SNR —` and blank profile.

## Operator check

Idle / noise, no TX peer: all LEDs dark, SNR —.  
FAC lock without file yet: FAC (and often Time/Frame/IO) green; MSC green only when MSC CRC OK (data flowing).
