#!/usr/bin/env bash
# Установка десктоп-клиента ZefiTime на Ubuntu/Debian (GUI).
# Установка не требует запущенного сервера — только этот репозиторий на диске.
#
# Из корня клонированного репозитория:
#   bash scripts/install-client-linux.sh
#
# С sudo при запросе (ставит python3-venv, python3-tk). Потом ярлык на рабочем столе.
#
# Если на рабочем столе «подозрительный» ярлык (Ubuntu): ПКМ → «Разрешить запуск».

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MAIN_PY="${REPO_ROOT}/main.py"
REQ="${REPO_ROOT}/requirements-client.txt"

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -f "${MAIN_PY}" ]] || die "Не найден ${MAIN_PY}. Запускайте скрипт из клонированного репозитория ZefiTime."
[[ -f "${REQ}" ]] || die "Не найден ${REQ}."

if [[ "${EUID:-0}" -eq 0 ]]; then
  die "Запускайте без sudo: bash scripts/install-client-linux.sh (скрипт сам вызовет sudo для apt)."
fi

if ! command -v apt-get >/dev/null 2>&1; then
  die "Нужен apt (Debian/Ubuntu). Установите вручную: python3-venv python3-tk python3-dev"
fi

echo "==> Установка системных пакетов (запрос пароля sudo)..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-tk python3-dev

CLIENT_DATA="${HOME}/.local/share/zefitime-client"
VENV="${CLIENT_DATA}/venv"
LAUNCHER="${HOME}/.local/bin/zefitime-client"
if command -v xdg-user-dir >/dev/null 2>&1; then
  DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
fi
if [[ -z "${DESKTOP_DIR}" || ! -d "${DESKTOP_DIR}" ]]; then
  DESKTOP_DIR="${HOME}/Desktop"
fi
APP_DIR="${HOME}/.local/share/applications"
ICON="${REPO_ROOT}/assets/logo.png"
[[ -f "${ICON}" ]] || ICON=""

mkdir -p "${CLIENT_DATA}" "${HOME}/.local/bin" "${APP_DIR}" "${DESKTOP_DIR}"

if [[ ! -d "${VENV}" ]]; then
  echo "==> Создание виртуального окружения клиента..."
  python3 -m venv "${VENV}"
fi

echo "==> Установка зависимостей Python..."
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
pip install --upgrade pip
pip install -r "${REQ}"

echo "==> Создание команды запуска: ${LAUNCHER}"
REPO_ESC=$(printf '%q' "${REPO_ROOT}")
cat >"${LAUNCHER}" <<EOF
#!/usr/bin/env bash
# Автоматически создано install-client-linux.sh
export PYTHONUNBUFFERED=1
cd ${REPO_ESC} || exit 1
exec "${VENV}/bin/python" main.py "\$@"
EOF
chmod +x "${LAUNCHER}"

make_desktop() {
  local dest="$1"
  {
    echo "[Desktop Entry]"
    echo "Type=Application"
    echo "Name=ZefiTime"
    echo "Comment=Клиент учёта времени ZefiTime"
    echo "Exec=${LAUNCHER}"
    echo "Terminal=false"
    echo "Categories=Office;GTK;"
    if [[ -n "${ICON}" && -f "${ICON}" ]]; then
      echo "Icon=${ICON}"
    fi
    echo "StartupNotify=true"
  } >"${dest}"
  chmod +x "${dest}"
}

echo "==> Ярлыки: рабочий стол и меню приложений"
make_desktop "${DESKTOP_DIR}/zefitime-client.desktop"
make_desktop "${APP_DIR}/zefitime-client.desktop"

echo ""
echo "Готово."
echo "  Запуск из терминала:  ${LAUNCHER}"
echo "  Или дважды щёлкните «ZefiTime» на рабочем столе (при необходимости: ПКМ → Разрешить запуск)."
echo "  Адрес сервера вводится в окне входа — сервер для установки клиента не нужен."
