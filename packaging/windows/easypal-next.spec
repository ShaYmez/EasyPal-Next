# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[1]

_redist_dir = project_root / "packaging" / "windows" / "redist"
_binaries = []
for _dll_name in (
    "libcodec2.dll",
    "libgcc_s_seh-1.dll",
    "libstdc++-6.dll",
    "libwinpthread-1.dll",
):
    _dll = _redist_dir / _dll_name
    if _dll.is_file():
        _binaries.append((str(_dll), "."))

_brand_ico = project_root / "resources" / "brand" / "easypal-next.ico"

_styles_dir = project_root / "src" / "easypal_next" / "ui" / "styles"
_datas = [
    (str(project_root / "config" / "defaults.yaml"), "config"),
    (str(project_root / "src" / "easypal_next" / "network" / "static"), "easypal_next/network/static"),
]
if _styles_dir.is_dir():
    _datas.append((str(_styles_dir), "ui/styles"))
try:
    import PySide6

    _imgfmt = Path(PySide6.__file__).resolve().parent / "plugins" / "imageformats"
    if _imgfmt.is_dir():
        _datas.append((str(_imgfmt), "PySide6/plugins/imageformats"))
except ImportError:
    pass
_brand_dir = project_root / "resources" / "brand"
if _brand_dir.is_dir():
    _datas.append((str(_brand_dir), "resources/brand"))

a = Analysis(
    [str(project_root / "src" / "easypal_next" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=_binaries,
    datas=_datas,
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
    icon=str(_brand_ico) if _brand_ico.is_file() else None,
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
