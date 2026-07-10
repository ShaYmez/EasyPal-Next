#!/usr/bin/env python3
"""Download libcodec2.dll and MinGW runtime deps from MSYS2 UCRT64 into redist/."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REDIST = ROOT / "packaging" / "windows" / "redist"
BASE_URL = "https://mirror.msys2.org/mingw/ucrt64/"

# Pinned MSYS2 UCRT64 packages
PACKAGES = [
    "mingw-w64-ucrt-x86_64-codec2-1.2.0-1-any.pkg.tar.zst",
    "mingw-w64-ucrt-x86_64-gcc-libs-16.1.0-5-any.pkg.tar.zst",
    "mingw-w64-ucrt-x86_64-libwinpthread-14.0.0.r179.g24aaa6147-1-any.pkg.tar.zst",
]

# DLLs required for ctypes to load libcodec2.dll on stock Windows
RUNTIME_DLLS = (
    "libcodec2.dll",
    "libgcc_s_seh-1.dll",
    "libstdc++-6.dll",
    "libwinpthread-1.dll",
)


def _ensure_zstandard():
    try:
        import zstandard  # noqa: F401
    except ImportError:
        print("Installing zstandard...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "zstandard", "-q"])
        import zstandard  # noqa: F401


def _extract_zst_tar(archive: Path, dest_dir: Path) -> None:
    import zstandard

    dctx = zstandard.ZstdDecompressor()
    with archive.open("rb") as zf:
        with dctx.stream_reader(zf) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(dest_dir, filter="data")
                else:
                    tar.extractall(dest_dir)


def _copy_dlls(extract_root: Path, dest: Path) -> list[str]:
    copied: list[str] = []
    for name in RUNTIME_DLLS:
        matches = list(extract_root.rglob(name))
        if not matches:
            continue
        shutil.copy2(matches[0], dest / name)
        copied.append(name)
    return copied


def _download(url: str, dest: Path, retries: int = 3) -> None:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            urllib.request.urlretrieve(url, dest)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt < retries:
                wait = attempt * 2
                print(f"  retry {attempt}/{retries - 1} in {wait}s ({exc})")
                time.sleep(wait)
    raise RuntimeError(f"download failed: {url}") from last_err


def main() -> int:
    REDIST.mkdir(parents=True, exist_ok=True)
    _ensure_zstandard()

    all_copied: set[str] = set()
    with tempfile.TemporaryDirectory() as tmp:
        extract_root = Path(tmp) / "all"
        extract_root.mkdir()

        for pkg in PACKAGES:
            print(f"Downloading {pkg}")
            pkg_path = Path(tmp) / pkg
            _download(BASE_URL + pkg, pkg_path)
            pkg_extract = Path(tmp) / pkg.replace(".pkg.tar.zst", "")
            pkg_extract.mkdir()
            _extract_zst_tar(pkg_path, pkg_extract)
            # merge into combined tree
            for item in pkg_extract.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(pkg_extract)
                    target = extract_root / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)

        for name in _copy_dlls(extract_root, REDIST):
            all_copied.add(name)

    missing = [n for n in RUNTIME_DLLS if n not in all_copied]
    if missing:
        print(f"ERROR: missing DLLs: {missing}")
        return 1

    print(f"OK: redist contains {', '.join(RUNTIME_DLLS)}")
    print("Run: python scripts/verify-codec2.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
