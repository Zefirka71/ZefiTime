# ZefiTime

**ZefiTime** is an open-source, self-hosted work-time tracking and task management system for small and medium-sized businesses. The server runs on Linux or Windows; the desktop client runs on Windows (no Python required) or Linux.

---

## Features

- **Time tracking** — start / pause / stop sessions with a one-click timer
- **Anti-AFK detection** — automatically pauses the timer when the employee steps away from the keyboard/mouse
- **Offline mode** — logs are saved locally and synced to the server automatically when the connection is restored
- **Task management** — create tasks, set deadlines, attach files, mark as done
- **Dashboard** — weekly hours chart and task overview at a glance
- **Excel export** — generate attendance reports directly from the Django admin panel
- **One-command deployment** — a single shell script sets up everything: Python venv, database, static files, admin account, and system service
- **Self-hosted** — all data stays inside your own network; no cloud subscriptions

---

## Tech stack

| Layer | Technology |
|---|---|
| Server | Python 3.12, Django 6.x, Django REST Framework 3.16 |
| Database | SQLite (default) — switch to PostgreSQL via `DATABASE_URL` |
| WSGI | gunicorn (Linux) / waitress (Windows) |
| Client | Python 3.12, CustomTkinter, Matplotlib |
| Client packaging | PyInstaller + Inno Setup 6 |
| Auth | HTTP Basic Auth over LAN (personnel-number login) |

---

## Quick start

### Server on Linux (Debian / Ubuntu)

```bash
git clone https://github.com/Zefirka71/ZefiTime.git
cd ZefiTime
sudo bash scripts/install-server-linux.sh
```

The script will:

1. Install system packages (`python3-venv`, `git`, etc.) via apt
2. Auto-install Python 3.12 via the deadsnakes PPA if the system Python is older
3. Create an isolated `zefitime` system user
4. Create a virtualenv and install all Python dependencies
5. Generate a `.env` file with a random `SECRET_KEY` and the server's IP in `ALLOWED_HOSTS`
6. Run `migrate` and `collectstatic`
7. Create an `admin` account with a randomly generated password
8. Register and start `zefitime.service` via systemd (auto-start on boot, gunicorn on port 8000)

When finished, the script prints a banner with the server address, admin login, and password. **Save the password — it is shown only once.**

```
================================================================================
  ZefiTime Server — installation complete
================================================================================

  Server address:   http://192.168.1.10:8000
  Admin panel:      http://192.168.1.10:8000/admin/

  Admin login:      admin
  Admin password:   xK9mP2nRqT8vWzAb

================================================================================
```

**Custom port:**

```bash
PORT=9000 sudo bash scripts/install-server-linux.sh
```

**Check service status:**

```bash
sudo systemctl status zefitime
sudo journalctl -u zefitime -e --no-pager
```

**Open firewall port (if needed):**

```bash
sudo ufw allow 8000/tcp && sudo ufw reload
```

---

### Server on Windows

```powershell
git clone https://github.com/Zefirka71/ZefiTime.git
cd ZefiTime
.\scripts\setup-server-windows.ps1
```

The script performs the same steps as the Linux version (venv, dependencies, `.env`, migrations, admin account) and then starts the server via **waitress** (a production-ready WSGI server for Windows). A banner with the server address and credentials is printed when ready.

> The Windows script does not register a Windows Service automatically.
> To enable auto-start, use Task Scheduler or [NSSM](https://nssm.cc/).

---

## Client installation

### Windows — installer (recommended, no Python needed)

1. Go to the [Releases](https://github.com/Zefirka71/ZefiTime/releases) page
2. Download `ZefiTime-Setup-x.x.x.exe`
3. Run the installer and follow the wizard — all dependencies are bundled (~94 MB)
4. Launch **ZefiTime** from the Start menu or the desktop shortcut
5. Enter your server address (`192.168.1.10:8000`) and personnel number

### Linux — script install

```bash
git clone https://github.com/Zefirka71/ZefiTime.git
cd ZefiTime
bash scripts/install-client-linux.sh
```

The script installs system packages (`python3-venv`, `python3-tk`), creates a virtualenv at `~/.local/share/zefitime-client/`, and adds a `.desktop` shortcut to your desktop and application menu. Running a server is not required to install the client.

---

## Project structure

```
ZefiTime/
├── server_app/               # Django server
│   ├── api/                  # Models, serializers, views, admin, auth
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── admin.py
│   │   └── authentication.py # Personnel-number auth backend
│   ├── core/                 # Django project settings, urls, wsgi
│   ├── requirements.txt
│   └── manage.py
├── modules/                  # Desktop client modules
│   ├── ui.py                 # All UI windows and tabs
│   ├── api_client.py         # REST API calls, offline sync
│   └── database.py           # Local SQLite (work_logs, settings)
├── main.py                   # Client entry point
├── requirements-client.txt   # Client-only dependencies
├── scripts/
│   ├── install-server-linux.sh   # One-command Linux server setup
│   ├── setup-server-windows.ps1  # One-command Windows server setup
│   └── install-client-linux.sh  # Linux client installer
└── packaging/
    ├── ZefiTimeClient.spec   # PyInstaller spec
    ├── ZefiTimeClient.iss    # Inno Setup script
    └── build_client.ps1      # Builds .exe + installer on Windows
```

---

## Environment variables

The server reads its configuration from `server_app/.env` (generated automatically by the install scripts). You can also create it manually based on `.env.example`:

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | **Required in production.** 50+ character random string |
| `DJANGO_DEBUG` | `False` | Set to `True` only for local development |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated list of allowed hosts / IPs |
| `DJANGO_USE_HTTPS` | `False` | Set to `True` if running behind an HTTPS proxy |

---

## Building the Windows client locally

Requires **Python 3.x**, **Inno Setup 6** installed at the default path.

```powershell
# From the repository root
.\packaging\build_client.ps1
```

Output:
- `dist\ZefiTime\ZefiTime.exe` — standalone executable
- `dist\installer\ZefiTime-Setup-1.0.0.exe` — Windows installer

---

## License

MIT — free to use, modify, and distribute.
