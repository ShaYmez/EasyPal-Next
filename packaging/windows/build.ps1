$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Write-Host "Building EasyPal-Next Windows release from $Root"

Push-Location $Root
try {
    if (-not (Test-Path "packaging/windows/redist/libcodec2.dll")) {
        Write-Warning "libcodec2.dll not found in packaging/windows/redist/ — installer will lack modem support."
    }

    pyinstaller --noconfirm "packaging/windows/easypal-next.spec" --distpath "packaging/windows/dist" --workpath "packaging/windows/build"

    if (Get-Command iscc -ErrorAction SilentlyContinue) {
        $Iscc = "iscc"
    } else {
        $IsccCandidates = @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        )
        $Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }

    if ($Iscc) {
        Push-Location "packaging/windows"
        try {
            & $Iscc "easypal-next.iss"
        } finally {
            Pop-Location
        }
        Write-Host "Installer written to packaging/windows/output/"
    } else {
        Write-Warning "Inno Setup (iscc) not found. PyInstaller bundle is at packaging/windows/dist/EasyPal-Next/"
    }
}
finally {
    Pop-Location
}
