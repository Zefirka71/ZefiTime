# Sborka Windows-klienta (onedir) cherez PyInstaller.
# Zapusk iz PowerShell, iz kornya repozitoriya:
#   Set-Location "C:\path\to\ZefiTime"
#   .\packaging\build_client.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPython = Join-Path $Root ".venv-client\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "==> Sozdanie .venv-client ..."
    py -3 -m venv .venv-client
    $venvPython = Join-Path $Root ".venv-client\Scripts\python.exe"
}

Write-Host "==> Ustanovka zavisimostey..."
& $venvPython -m pip install --upgrade pip -q
& $venvPython -m pip install -r requirements-client.txt pyinstaller -q

Write-Host "==> Sborka .exe cherez PyInstaller..."
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
    Write-Host "==> Sborka ustanovshchika Inno Setup: $iscc"
    & $iscc (Join-Path $Root "packaging\ZefiTimeClient.iss")
    Write-Host "Installer: $Root\dist\installer\ZefiTime-Setup-1.0.0.exe"
} else {
    Write-Host "Inno Setup 6 not found - skipping installer."
    Write-Host "Install from https://jrsoftware.org/isdl.php then re-run."
}
