# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[1]

_redist_dll = project_root / "packaging" / "windows" / "redist" / "libcodec2.dll"
_binaries = []
if _redist_dll.is_file():
    _binaries.append((str(_redist_dll), "."))

a = Analysis(
    [str(project_root / "src" / "easypal_next" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=_binaries,
    datas=[
        (str(project_root / "config" / "defaults.yaml"), "config"),
        (str(project_root / "src" / "easypal_next" / "network" / "static"), "easypal_next/network/static"),
    ],
    hiddenimports=[
        "sounddevice",
        "numpy",
        "zfec",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EasyPal-Next",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EasyPal-Next",
)
