# EasyPal-Next Windows packaging

Copyright (c) 2026 Shane Daley M0VUB (ShaYmez) <shane@freestar.network>

Production releases ship as **EasyPal-Next-Setup-x.y.z.exe** built with PyInstaller + Inno Setup.

## Prerequisites

- Windows 10/11
- Python 3.11+ with project dependencies installed
- [Inno Setup 6](https://jrsoftware.org/isinfo.php)
- `libcodec2.dll` placed in `packaging/windows/redist/libcodec2.dll`

## Build steps

```powershell
pip install -e ".[packaging]"
.\packaging\windows\build.ps1
```

Output: `packaging/windows/output/EasyPal-Next-Setup-0.1.0.exe`

## What gets bundled

- `EasyPal-Next.exe` (PyInstaller onedir entry point)
- Python runtime and pip dependencies
- `libcodec2.dll`
- `config/defaults.yaml`, mobile gallery static files, icons

## User data (preserved on upgrade/uninstall)

- `%APPDATA%\EasyPal-Next\config.yaml`
- `%APPDATA%\EasyPal-Next\gallery\`
- `%APPDATA%\EasyPal-Next\logs\`

## Code signing

Unsigned builds may trigger SmartScreen. Document EV code signing for release maintainers.
