#!/usr/bin/env bash
# Установка сервера на Linux (Debian/Ubuntu, VPS). Запуск из корня клонированного репозитория:
#   git clone https://github.com/YOU/REPO.git && cd REPO
#   sudo bash scripts/install-server-linux.sh
#
# Опции:
#   PORT=8000              — порт gunicorn
#   SERVICE_USER=...       — пользователь systemd/gunicorn (по умолчанию см. ниже)
#
# Если клон в /home/ВАШ_ЛОГИН/... (VirtualBox), пользователь zefitime не может зайти
# в чужой $HOME (часто 700) — будет «Отказано в доступе» на cd .../server_app.
# Тогда скрипт берёт владельца репозитория. На VPS в /opt/... по умолчанию — zefitime.

set -euo pipefail

PORT="${PORT:-8000}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_DIR="${REPO_ROOT}/server_app"
VENV="${SERVER_DIR}/.venv"

REPO_OWNER="$(stat -c '%U' "${REPO_ROOT}")"
if [[ "${REPO_ROOT}" == /home/* ]]; then
  SERVICE_USER="${SERVICE_USER:-${REPO_OWNER}}"
  echo "Репозиторий в \$HOME — сервис будет работать от пользователя: ${SERVICE_USER}"
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

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

if [[ "${SERVICE_USER}" == zefitime ]] && ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home "${SERVER_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}" || true
fi

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${SERVER_DIR}"

sudo -u "${SERVICE_USER}" bash <<EOSU
set -euo pipefail
cd "${SERVER_DIR}"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
if [[ ! -f .env ]]; then
  cp .env.example .env
fi
python manage.py migrate --noinput
python manage.py collectstatic --noinput
EOSU

echo ""
echo "Создайте суперпользователя (один раз):"
echo "  sudo -u ${SERVICE_USER} -H bash -lc 'cd ${SERVER_DIR} && . .venv/bin/activate && python manage.py createsuperuser'"
echo ""
echo "Перед продакшеном отредактируйте ${SERVER_DIR}/.env :"
echo "  DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS=ваш_домен_или_IP"
echo "  При HTTP без TLS оставьте DJANGO_USE_HTTPS=False"
echo ""

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

echo "Сервис zefitime слушает 0.0.0.0:${PORT}"
echo "Клиенту: http://<IP_сервера>:${PORT}/  (табельный номер + пароль из админки)"
