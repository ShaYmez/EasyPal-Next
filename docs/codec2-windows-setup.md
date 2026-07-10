# libcodec2 / FreeDV Setup on Windows

EasyPal-Next loads `libcodec2.dll` at runtime for DATAC3 modem TX/RX.

## Quick verify

```bat
cd EasyPal-Next
.venv\Scripts\activate
python scripts\verify-codec2.py
```

Exit code 0 means the DLL loads and `freedv_open(DATAC3)` succeeded.

## Option A — Build from source (MSYS2)

1. Install [MSYS2](https://www.msys2.org/)
2. In **MSYS2 UCRT64** terminal:

```bash
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake make
git clone https://github.com/drowe67/codec2.git
cd codec2
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

3. Copy `build/src/libcodec2.dll` to:

```
packaging/windows/redist/libcodec2.dll
```

4. Add to `%APPDATA%\EasyPal-Next\config.yaml`:

```yaml
modem:
  libcodec2_path: "C:/Users/YOU/EasyPal-Next/packaging/windows/redist/libcodec2.dll"
```

## Option B — Fetch MSYS2 UCRT64 packages (recommended for dev)

From the project root with `.venv` activated:

```bat
python scripts\fetch-libcodec2.py
python scripts\verify-codec2.py
```

This downloads pinned MSYS2 UCRT64 packages and copies these DLLs into `packaging/windows/redist/`:

- `libcodec2.dll`
- `libgcc_s_seh-1.dll`
- `libstdc++-6.dll`
- `libwinpthread-1.dll`

The MinGW runtime DLLs must sit next to `libcodec2.dll` on stock Windows (PyInstaller bundles all four).

## Option C — Pre-built DLL (if available)

Place `libcodec2.dll` and its MinGW dependencies in `packaging/windows/redist/` or next to `EasyPal-Next.exe` after install.

## Dependencies

MSYS2 builds typically need the MinGW runtime DLLs listed above, not only MSVC runtime.

If load still fails, install [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

## References

- https://github.com/drowe67/codec2
- [README_data.md](https://github.com/drowe67/codec2/blob/main/README_data.md) — raw data API
