# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Huawei EMS B1 Battery Manager across macOS, Windows, and Linux."""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

ROOT_DIR = Path(SPECPATH).resolve() if "SPECPATH" in locals() else Path.cwd().resolve()
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
DATA_DIR = ROOT_DIR / "backend" / "app" / "data"

datas = [
    (str(FRONTEND_DIST), "frontend/dist"),
    (str(FRONTEND_DIST), "dist"),
    (str(DATA_DIR), "app/data"),
    (str(DATA_DIR), "data"),
]

binaries = []

try:
    datas += collect_data_files("certifi")
except Exception:
    pass

if sys.platform == "win32":
    try:
        from PyInstaller.utils.hooks import collect_dynamic_libs
        datas += collect_data_files("webview")
        binaries += collect_dynamic_libs("webview")
    except Exception:
        pass
    try:
        from PyInstaller.utils.hooks import collect_dynamic_libs
        datas += collect_data_files("pythonnet")
        binaries += collect_dynamic_libs("pythonnet")
    except Exception:
        pass

# Explicitly ensure webview runtime binaries and interop DLLs are bundled in root, _internal, and webview/lib
try:
    import webview
    webview_lib = Path(webview.__file__).parent / "lib"
    if webview_lib.exists():
        for item in webview_lib.iterdir():
            if item.is_file():
                datas.append((str(item), "."))
                datas.append((str(item), "webview/lib"))
            elif item.is_dir() and item.name == "runtimes":
                for arch in ["win-x64", "win-x86", "win-arm64"]:
                    native_dir = item / arch / "native"
                    if native_dir.exists():
                        for dll in native_dir.glob("*.dll"):
                            datas.append((str(dll), "."))
                            datas.append((str(dll), f"webview/lib/runtimes/{arch}/native"))
                            datas.append((str(dll), f"runtimes/{arch}/native"))
except Exception:
    pass

# Collect hidden submodules
hiddenimports = [
    "certifi",
    "ssl",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "pydantic",
    "serial",
    "serial.tools",
    "serial.tools.list_ports",
    "serial.tools.list_ports_osx",
    "serial.tools.list_ports_posix",
    "serial.tools.list_ports_windows",
    "serial.serialwin32",
    "sqlite3",
    "aiosqlite",
    "webview",
    "ctypes",
    "multiprocessing",
]

# Platform-specific webview modules
if sys.platform == "darwin":
    hiddenimports.extend([
        "webview.platforms.cocoa",
        "objc",
        "Foundation",
        "AppKit",
        "WebKit",
    ])
elif sys.platform == "win32":
    hiddenimports.extend([
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "webview.platforms.mshtml",
        "webview.platforms.win32",
        "clr",
        "pythonnet",
        "clr_loader",
        "winreg",
        "ctypes.wintypes",
    ])
else:
    hiddenimports.extend([
        "webview.platforms.gtk",
        "webview.platforms.qt",
    ])

# Optional icons
icon_file = None
if sys.platform == "darwin" and (ROOT_DIR / "assets" / "HuaweiEMS.icns").exists():
    icon_file = str(ROOT_DIR / "assets" / "HuaweiEMS.icns")
elif (ROOT_DIR / "assets" / "icon.ico").exists():
    icon_file = str(ROOT_DIR / "assets" / "icon.ico")
elif (ROOT_DIR / "assets" / "icon.png").exists() and sys.platform != "win32":
    icon_file = str(ROOT_DIR / "assets" / "icon.png")

a = Analysis(
    [str(ROOT_DIR / "backend" / "app" / "desktop.py")],
    pathex=[str(ROOT_DIR / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "notebook", "IPython"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HuaweiEMSManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HuaweiEMSManager",
)

# macOS Application Bundle (.app)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Huawei EMS B1 Battery Manager.app",
        icon=icon_file,
        bundle_identifier="com.huawei.bms.manager",
        info_plist={
            "CFBundleShortVersionString": "1.1.5",
            "CFBundleVersion": "1.1.5",
            "NSHighResolutionCapable": "True",
            "NSRequiresAquaSystemAppearance": "False",
            "LSMinimumSystemVersion": "10.15",
            "NSHumanReadableCopyright": "Copyright © 2026 Huawei EMS B1 Battery Manager",
        },
    )
