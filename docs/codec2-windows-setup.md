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

## Option B — Pre-built DLL (if available)

Place `libcodec2.dll` in `packaging/windows/redist/` or next to `EasyPal-Next.exe` after install.

## Dependencies

`libcodec2.dll` may require MSVC runtime (`vcruntime140.dll`) — install
[Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if load fails.

## References

- https://github.com/drowe67/codec2
- [README_data.md](https://github.com/drowe67/codec2/blob/main/README_data.md) — raw data API
