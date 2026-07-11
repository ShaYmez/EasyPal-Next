# Native HamDRM (x64)

Vendored from [DazDSP/hamdrm-dll](https://github.com/DazDSP/hamdrm-dll) with CMake + FFTW3 shim for 64-bit EasyPal-Next.

## Build (Windows)

1. Download FFTW 3.3.5 Win64 zip into `native/deps/fftw64/` (or run the fetch step in `scripts/build-hamdrm-x64.sh`).
2. Use MinGW-w64 g++ (portable winlibs under `native/deps/mingw64/`) **or** VS 2022 x64 Build Tools.
3. Run:

```bash
scripts/build-hamdrm-x64.sh
```

Output: `native/hamdrm-dll/build-x64/bin/hamdrm.dll` (+ `libfftw3-3.dll`).

## Notes

- Upstream linked FFTW2 (`libfftw.lib`); we use FFTW3 via `compat/fftw2_compat.*`.
- SIMD/MMX asm paths stay disabled (`USE_SIMD` undefined).
- Copy both DLLs next to EasyPal-Next or into `%APPDATA%\EasyPal-Next\`.
