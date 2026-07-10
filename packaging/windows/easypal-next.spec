# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[2]

a = Analysis(
    [str(project_root / "src" / "easypal_next" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=[
        (str(project_root / "packaging" / "windows" / "redist" / "libcodec2.dll"), "."),
    ],
    datas=[
        (str(project_root / "config" / "defaults.yaml"), "config"),
        (str(project_root / "src" / "easypal_next" / "network" / "static"), "easypal_next/network/static"),
    ],
    hiddenimports=[
        "sounddevice",
        "numpy",
        "zfec",
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
