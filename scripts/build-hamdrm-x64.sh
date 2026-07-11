#!/usr/bin/env bash
# Build 64-bit hamdrm.dll with VS Build Tools + CMake.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HAMDRM="$ROOT/native/hamdrm-dll"
BUILD="$HAMDRM/build-x64"
CMAKE="${CMAKE:-/c/Program Files/CMake/bin/cmake.exe}"

VCVARS="${VCVARS:-/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat}"
if [[ ! -f "$VCVARS" ]]; then
  VCVARS="/c/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
fi
if [[ ! -f "$VCVARS" ]]; then
  echo "vcvars64.bat not found. Install VS 2022 C++ x64 tools." >&2
  exit 1
fi

mkdir -p "$BUILD"

# Run cmake/build inside an x64 MSVC environment (cmd).
VCVARS_WIN="$(cygpath -w "$VCVARS" 2>/dev/null || echo "$VCVARS")"
HAMDRM_WIN="$(cygpath -w "$HAMDRM" 2>/dev/null || echo "$HAMDRM")"
BUILD_WIN="$(cygpath -w "$BUILD" 2>/dev/null || echo "$BUILD")"
CMAKE_WIN="$(cygpath -w "$CMAKE" 2>/dev/null || echo "$CMAKE")"

cmd.exe //c "call \"${VCVARS_WIN}\" && \"${CMAKE_WIN}\" -S \"${HAMDRM_WIN}\" -B \"${BUILD_WIN}\" -G \"Ninja\" -DCMAKE_BUILD_TYPE=Release" \
  || cmd.exe //c "call \"${VCVARS_WIN}\" && \"${CMAKE_WIN}\" -S \"${HAMDRM_WIN}\" -B \"${BUILD_WIN}\" -G \"Visual Studio 17 2022\" -A x64 -DCMAKE_BUILD_TYPE=Release"

cmd.exe //c "call \"${VCVARS_WIN}\" && \"${CMAKE_WIN}\" --build \"${BUILD_WIN}\" --config Release --parallel"

echo "Built:"
find "$BUILD" -name 'hamdrm.dll' 2>/dev/null
