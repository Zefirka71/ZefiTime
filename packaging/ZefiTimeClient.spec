# -*- mode: python ; coding: utf-8 -*-
# Сборка: из корня репозитория
#   pyinstaller packaging\ZefiTimeClient.spec --noconfirm
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPEC).resolve().parent.parent
main_script = project_root / "main.py"
assets = project_root / "assets"

datas = [(str(assets), "assets")]
datas += collect_data_files("customtkinter")
datas += collect_data_files("matplotlib")

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_agg",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ZefiTime",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets / "logo.ico") if (assets / "logo.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ZefiTime",
)
