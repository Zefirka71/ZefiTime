#!/usr/bin/env bash
# Установка сервера ZefiTime на Linux (Debian/Ubuntu, VPS или WSL). Запуск из корня клонированного репозитория:
#   git clone https://github.com/YOU/REPO.git && cd REPO
#   sudo bash scripts/install-server-linux.sh
#
# Опции (переменные окружения):
#   PORT=8000              — порт gunicorn (по умолчанию 8000)
#   SERVICE_USER=...       — пользователь systemd/gunicorn
#
# После установки скрипт выведет IP, логин и пароль администратора.

set -euo pipefail

PORT="${PORT:-8000}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_DIR="${REPO_ROOT}/server_app"
VENV="${SERVER_DIR}/.venv"
ENV_FILE="${SERVER_DIR}/.env"

REPO_OWNER="$(stat -c '%U' "${REPO_ROOT}")"
if [[ "${REPO_ROOT}" == /home/* ]]; then
  SERVICE_USER="${SERVICE_USER:-${REPO_OWNER}}"
else
  SERVICE_USER="${SERVICE_USER:-zefitime}"
fi

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -f "${SERVER_DIR}/manage.py" ]] || die "Не найден ${SERVER_DIR}/manage.py. Запускайте из корня репозитория после git clone."

if [[ "${EUID:-0}" -ne 0 ]]; then
  die "Нужны права root: sudo bash scripts/install-server-linux.sh"
fi

if ! command -v apt-get >/dev/null 2>&1; then
  die "Ожидается apt (Debian/Ubuntu). На других дистрибутивах установите python3-venv, git вручную."
fi

# ── Зависимости ─────────────────────────────────────────────────────────────
echo "==> Установка системных пакетов..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git software-properties-common

# ── Python 3.12+ (Django 6.x требует >= 3.12) ────────────────────────────────
PYTHON_CMD=python3
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
  echo "==> Python < 3.12 обнаружен ($(python3 --version 2>&1 | awk '{print $2}')), устанавливаю Python 3.12..."
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update -qq
  apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
  PYTHON_CMD=python3.12
  echo "    Python 3.12 установлен."
else
  echo "==> $(python3 --version 2>&1) — подходит, дополнительная установка не нужна."
fi

# ── Пользователь сервиса ─────────────────────────────────────────────────────
if [[ "${SERVICE_USER}" == zefitime ]] && ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home "${SERVER_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}" || true
fi

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${SERVER_DIR}"

# ── Определяем IP сервера ────────────────────────────────────────────────────
# Берём первый не-loopback IPv4 адрес.
SERVER_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^$' | grep -v '^127\.' | head -1 || true)"
if [[ -z "${SERVER_IP}" ]]; then
  SERVER_IP="$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' || true)"
fi
if [[ -z "${SERVER_IP}" ]]; then
  SERVER_IP="127.0.0.1"
  echo "ВНИМАНИЕ: Не удалось определить внешний IP, использую 127.0.0.1"
fi

# ── venv, зависимости, .env ──────────────────────────────────────────────────
echo "==> Создание виртуального окружения и установка зависимостей..."
sudo -u "${SERVICE_USER}" bash <<EOSU
set -eo pipefail
cd "${SERVER_DIR}"
${PYTHON_CMD} -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt
EOSU

# ── Генерация .env ───────────────────────────────────────────────────────────
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "==> Создание .env..."
  SECRET_KEY="$(python3 -c "import secrets, string; \
    chars=string.ascii_letters+string.digits+'!@\$%^&*(-_=+)'; \
    print(''.join(secrets.choice(chars) for _ in range(50)))")"
  cat >"${ENV_FILE}" <<EOF
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${SERVER_IP},localhost,127.0.0.1
DJANGO_USE_HTTPS=False
EOF
  chown "${SERVICE_USER}:${SERVICE_USER}" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "    .env создан (SECRET_KEY сгенерирован автоматически)"
else
  echo "==> .env уже существует, пропускаю генерацию."
  # Добавляем IP в ALLOWED_HOSTS если его там нет
  if ! grep -q "DJANGO_ALLOWED_HOSTS" "${ENV_FILE}"; then
    echo "DJANGO_ALLOWED_HOSTS=${SERVER_IP},localhost,127.0.0.1" >>"${ENV_FILE}"
  elif ! grep "DJANGO_ALLOWED_HOSTS" "${ENV_FILE}" | grep -q "${SERVER_IP}"; then
    sed -i "s/^DJANGO_ALLOWED_HOSTS=.*/&,${SERVER_IP}/" "${ENV_FILE}"
    echo "    IP ${SERVER_IP} добавлен в ALLOWED_HOSTS"
  fi
fi

# ── Миграции и статика ────────────────────────────────────────────────────────
echo "==> Применение миграций..."
sudo -u "${SERVICE_USER}" bash <<EOSU
set -euo pipefail
cd "${SERVER_DIR}"
. .venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
EOSU

# ── Создание администратора ───────────────────────────────────────────────────
ADMIN_USER="admin"
ADMIN_PASS="$(python3 -c "import secrets, string; \
  chars = string.ascii_letters + string.digits; \
  print(''.join(secrets.choice(chars) for _ in range(16)))")"

# Создаём superuser только если такого пользователя ещё нет
SUPERUSER_EXISTS="$(sudo -u "${SERVICE_USER}" bash -c "
  cd '${SERVER_DIR}'
  .venv/bin/python manage.py shell -c \"from django.contrib.auth import get_user_model; \
    User = get_user_model(); print(User.objects.filter(username='${ADMIN_USER}').exists())\"
")"

if [[ "${SUPERUSER_EXISTS}" == "True" ]]; then
  echo "==> Суперпользователь '${ADMIN_USER}' уже существует, пароль не меняю."
  ADMIN_PASS="(задан ранее — пароль не сбрасывается)"
else
  echo "==> Создание суперпользователя..."
  sudo -u "${SERVICE_USER}" bash -c "
    cd '${SERVER_DIR}'
    export DJANGO_SUPERUSER_USERNAME='${ADMIN_USER}'
    export DJANGO_SUPERUSER_PASSWORD='${ADMIN_PASS}'
    export DJANGO_SUPERUSER_EMAIL='admin@localhost'
    .venv/bin/python manage.py createsuperuser --noinput
  "
fi

# ── systemd unit ──────────────────────────────────────────────────────────────
echo "==> Настройка systemd-сервиса..."
UNIT="/etc/systemd/system/zefitime.service"
cat >"${UNIT}" <<EOF
[Unit]
Description=ZefiTime Django (gunicorn)
After=network.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${SERVER_DIR}
ExecStart=${VENV}/bin/gunicorn --bind 0.0.0.0:${PORT} --workers 3 core.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable zefitime.service
systemctl restart zefitime.service

# ── Итоговый баннер ───────────────────────────────────────────────────────────
cat <<EOF

================================================================================
  ZefiTime Server — установка завершена успешно
================================================================================

  Адрес сервера (API + клиент):  http://${SERVER_IP}:${PORT}
  Веб-администратор:             http://${SERVER_IP}:${PORT}/admin/

  Логин администратора:  ${ADMIN_USER}
  Пароль администратора: ${ADMIN_PASS}

  СОХРАНИТЕ эти данные — пароль больше нигде не отображается.

================================================================================

  Далее:
  1. Откройте http://${SERVER_IP}:${PORT}/admin/ в браузере (с любого устройства в сети)
  2. Войдите с логином/паролем выше
  3. Создайте учётные записи сотрудников (раздел «Сотрудники»)
  4. В клиенте ZefiTime укажите адрес сервера: ${SERVER_IP}:${PORT}

  Статус службы:
    sudo systemctl status zefitime

  Если что-то пошло не так:
    sudo journalctl -u zefitime -e --no-pager

  Если фаервол блокирует порт ${PORT}:
    sudo ufw allow ${PORT}/tcp && sudo ufw reload

================================================================================
EOF
