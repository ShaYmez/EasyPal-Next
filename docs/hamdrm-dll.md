# HamDRM DLL notes (32-bit EasyPal vs 64-bit EasyPal-Next)

## Discovery on this machine

| Item | Result |
|------|--------|
| `hamdrm.dll` | **Not found** anywhere |
| EasyPal DRM API | **`C:\Program Files\EasyPal\run.dll`** — exports match [hamdrm.h](https://github.com/DazDSP/hamdrm-dll/blob/master/hamdrm.h) |
| `run.dll` bitness | **32-bit (I386)** |
| EasyPal-Next Python | **64-bit** |
| In-process load | **Fails** with WinError 193 |

Probe with:

```bat
.venv\Scripts\python scripts\find-hamdrm.py
```

## Current behaviour

1. Settings default engine = **HamDRM**
2. Factory tries to load `run.dll` / `hamdrm.dll`
3. On bitness mismatch → **fallback to FreeDV** with a clear log/status warning
4. Always-on Auto RX still works on the FreeDV path

## Path to real EasyPal interop

1. **64-bit HamDRM DLL (in progress)** — vendored sources under `native/hamdrm-dll/` (from [DazDSP/hamdrm-dll](https://github.com/DazDSP/hamdrm-dll)), built as x64 with FFTW3 + FFTW2 shim:

   ```bash
   scripts/build-hamdrm-x64.sh
   ```

   Place the resulting `hamdrm.dll` and `libfftw3-3.dll` in `%APPDATA%\EasyPal-Next\` or `packaging/windows/redist/`.

2. **32-bit bridge process** — small helper EXE that loads `run.dll` and speaks JSON-RPC over a pipe to 64-bit EasyPal-Next (planned follow-up)

3. **32-bit Python build of EasyPal-Next** — not preferred

Until a loadable 64-bit DLL is installed, FreeDV/EPNX remains the working on-air engine for Next↔Next transfers.
