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
        iscc "packaging/windows/easypal-next.iss"
        Write-Host "Installer written to packaging/windows/output/"
    } else {
        Write-Warning "Inno Setup (iscc) not found. PyInstaller bundle is at packaging/windows/dist/EasyPal-Next/"
    }
}
finally {
    Pop-Location
}
