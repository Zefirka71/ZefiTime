# Сборка Windows-клиента (onedir) через PyInstaller.
# Запуск из PowerShell, из любой папки:
#   Set-Location "C:\path\to\KOD_BKR-copy9"
#   .\packaging\build_client.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPython = Join-Path $Root ".venv-client\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv-client ..."
    py -3 -m venv .venv-client
    $venvPython = Join-Path $Root ".venv-client\Scripts\python.exe"
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements-client.txt pyinstaller

& $venvPython -m PyInstaller packaging\ZefiTimeClient.spec --noconfirm

Write-Host ""
Write-Host "PyInstaller done. Run: $Root\dist\ZefiTime\ZefiTime.exe"

$iscc = $null
foreach ($dir in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )) {
    if (Test-Path $dir) { $iscc = $dir; break }
}
if (-not $iscc) {
    $cmd = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}

if ($iscc) {
    Write-Host "Building installer with Inno Setup: $iscc"
    & $iscc (Join-Path $Root "packaging\ZefiTimeClient.iss")
    Write-Host "Installer: $Root\dist\installer\ZefiTime-Setup-*.exe"
} else {
    Write-Host ""
    Write-Host "Inno Setup 6 not found — skipping .exe installer."
    Write-Host "Install from https://jrsoftware.org/isinfo.php , then re-run this script or open packaging\ZefiTimeClient.iss in Inno and click Compile."
}
