# Установка и запуск сервера ZefiTime на Windows (локальная сеть / тест).
# Запуск из корня репозитория (от имени обычного пользователя):
#   .\scripts\setup-server-windows.ps1
#
# После завершения скрипт выведет IP сервера, логин и пароль администратора.
# Сервер запустится через waitress (production-WSGI, не dev-runserver).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ServerDir = Join-Path $Root "server_app"
$EnvFile = Join-Path $ServerDir ".env"

Set-Location $ServerDir

# ── venv ─────────────────────────────────────────────────────────────────────
$VenvPy = Join-Path $ServerDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Host "==> Создание виртуального окружения..."
    py -3 -m venv .venv
}

Write-Host "==> Установка зависимостей..."
& $VenvPy -m pip install --upgrade pip -q
& $VenvPy -m pip install -r requirements.txt waitress -q

# ── Определяем IP ─────────────────────────────────────────────────────────────
$ServerIP = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.PrefixOrigin -ne 'WellKnown' } |
    Sort-Object InterfaceMetric |
    Select-Object -First 1 -ExpandProperty IPAddress
)
if (-not $ServerIP) { $ServerIP = "127.0.0.1" }

$Port = 8000

# ── Генерация .env ────────────────────────────────────────────────────────────
if (-not (Test-Path $EnvFile)) {
    Write-Host "==> Создание .env (SECRET_KEY генерируется автоматически)..."
    $SecretKey = & $VenvPy -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    @"
DJANGO_SECRET_KEY=$SecretKey
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$ServerIP,localhost,127.0.0.1
DJANGO_USE_HTTPS=False
"@ | Out-File -FilePath $EnvFile -Encoding utf8
} else {
    Write-Host "==> .env уже существует, пропускаю генерацию."
    # Добавляем IP в ALLOWED_HOSTS если его там нет
    $envContent = Get-Content $EnvFile -Raw
    if ($envContent -notmatch [regex]::Escape($ServerIP)) {
        $envContent = $envContent -replace '(?m)^(DJANGO_ALLOWED_HOSTS=.*)$', "`$1,$ServerIP"
        $envContent | Out-File -FilePath $EnvFile -Encoding utf8 -NoNewline
        Write-Host "    IP $ServerIP добавлен в ALLOWED_HOSTS"
    }
}

# ── Миграции и статика ────────────────────────────────────────────────────────
Write-Host "==> Применение миграций..."
& $VenvPy manage.py migrate --noinput

Write-Host "==> Сборка статических файлов..."
& $VenvPy manage.py collectstatic --noinput

# ── Создание администратора ───────────────────────────────────────────────────
$AdminUser = "admin"
$AdminExists = & $VenvPy manage.py shell -c @"
from django.contrib.auth import get_user_model
User = get_user_model()
print(User.objects.filter(username='$AdminUser').exists())
"@

if ($AdminExists.Trim() -eq "True") {
    Write-Host "==> Суперпользователь '$AdminUser' уже существует."
    $AdminPass = "(задан ранее — пароль не сбрасывается)"
} else {
    Write-Host "==> Создание суперпользователя..."
    # Генерируем пароль: 16 символов из букв и цифр
    $AdminPass = & $VenvPy -c @"
import secrets, string
chars = string.ascii_letters + string.digits
print(''.join(secrets.choice(chars) for _ in range(16)))
"@
    $AdminPass = $AdminPass.Trim()

    $env:DJANGO_SUPERUSER_USERNAME = $AdminUser
    $env:DJANGO_SUPERUSER_PASSWORD = $AdminPass
    $env:DJANGO_SUPERUSER_EMAIL    = "admin@localhost"
    & $VenvPy manage.py createsuperuser --noinput
    Remove-Item Env:\DJANGO_SUPERUSER_USERNAME, Env:\DJANGO_SUPERUSER_PASSWORD, Env:\DJANGO_SUPERUSER_EMAIL
}

# ── Итоговый баннер ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================================"
Write-Host "  ZefiTime Server — готов к работе"
Write-Host "================================================================================"
Write-Host ""
Write-Host "  Адрес сервера (API + клиент):  http://${ServerIP}:${Port}"
Write-Host "  Веб-администратор:             http://${ServerIP}:${Port}/admin/"
Write-Host ""
Write-Host "  Логин администратора:  $AdminUser"
Write-Host "  Пароль администратора: $AdminPass"
Write-Host ""
Write-Host "  СОХРАНИТЕ эти данные — пароль больше нигде не отображается."
Write-Host ""
Write-Host "================================================================================"
Write-Host ""
Write-Host "  Далее:"
Write-Host "  1. Откройте http://${ServerIP}:${Port}/admin/ в браузере"
Write-Host "  2. Войдите с логином/паролем выше"
Write-Host "  3. Создайте учётные записи сотрудников"
Write-Host "  4. В клиенте ZefiTime укажите адрес: ${ServerIP}:${Port}"
Write-Host ""
Write-Host "  Если с другого ПК/телефона не открывается — разрешите порт $Port"
Write-Host "  в брандмауэре Windows (Пуск → Безопасность Windows → Брандмауэр)."
Write-Host ""
Write-Host "================================================================================"
Write-Host ""
Write-Host "  Сервер запускается... (Ctrl+C для остановки)"
Write-Host ""

# ── Запуск через waitress (production WSGI) ───────────────────────────────────
& $VenvPy -m waitress --listen="0.0.0.0:$Port" core.wsgi:application
