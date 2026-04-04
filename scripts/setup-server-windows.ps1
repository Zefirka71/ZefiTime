# Локальный запуск сервера на Windows (ноутбук) для тестов.
# Запуск из корня репозитория:
#   .\scripts\setup-server-windows.ps1
# После настройки поднимает Django на 0.0.0.0:8000 — клиент может стучаться по IP ноутбука в LAN.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ServerDir = Join-Path $Root "server_app"
Set-Location $ServerDir

$venvPy = Join-Path $ServerDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Creating server_app\.venv ..."
    py -3 -m venv .venv
    $venvPy = Join-Path $ServerDir ".venv\Scripts\python.exe"
}

& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt

$envExample = Join-Path $ServerDir ".env.example"
$envFile = Join-Path $ServerDir ".env"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "Created server_app\.env from .env.example (edit if needed)."
    }
}

Write-Host "Running migrations..."
& $venvPy manage.py migrate

Write-Host ""
Write-Host "If you need Django admin, create superuser once:"
Write-Host "  .\.venv\Scripts\python.exe manage.py createsuperuser"
Write-Host ""
Write-Host "Starting server on http://0.0.0.0:8000/ (all interfaces). Ctrl+C to stop."
& $venvPy manage.py runserver 0.0.0.0:8000
