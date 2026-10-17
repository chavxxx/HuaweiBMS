#!/usr/bin/env python3
"""Cross-Platform Standalone Installer Builder for Huawei EMS B1 Battery Manager.

Detects host OS (Windows, macOS, Linux), ensures frontend is built, runs PyInstaller,
and generates the platform-specific installer:
- macOS: Generates 'Huawei EMS B1 Battery Manager.app' and '.dmg' disk image installer.
- Windows: Generates 'HuaweiEMSManager.exe' and prepares Inno Setup installer.
- Linux: Generates standalone binary bundle and tar.gz installer with install.sh.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FRONTEND = ROOT / "frontend"
ASSETS = ROOT / "assets"
SYSTEM = platform.system()


def log(step: str, msg: str):
    print(f"\n\033[1;36m[{step}]\033[0m \033[1m{msg}\033[0m")


def run(cmd, cwd=None):
    print(f"  > {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd or ROOT, shell=isinstance(cmd, str))
    if res.returncode != 0:
        print(f"\n\033[1;31mERROR: Command failed with exit code {res.returncode}\033[0m")
        sys.exit(res.returncode)


def check_prerequisites():
    log("1/4", f"Checking build environment on {SYSTEM} ({platform.machine()})...")
    
    # Check node and npm
    npm_path = shutil.which("npm")
    if not npm_path:
        print("ERROR: Node.js / npm is required to compile the React frontend.")
        sys.exit(1)
    print(f"  Found npm: {npm_path}")

    # Check python
    print(f"  Python: {sys.version.split()[0]}")


def build_frontend():
    log("2/4", "Compiling production React/TypeScript frontend...")
    run(["npm", "install"], cwd=FRONTEND)
    run(["npm", "run", "build"], cwd=FRONTEND)
    
    index_html = FRONTEND / "dist" / "index.html"
    if not index_html.exists():
        print(f"ERROR: Frontend build output not found at {index_html}")
        sys.exit(1)
    print("  React production bundle successfully built in frontend/dist.")


def package_executable():
    log("3/4", f"Packaging standalone desktop application with PyInstaller on {SYSTEM}...")
    
    # Find pyinstaller in current venv or system
    pyinstaller = shutil.which("pyinstaller")
    venv_pyi = ROOT / "backend" / "venv" / "bin" / "pyinstaller"
    venv_pyi_win = ROOT / "backend" / "venv" / "Scripts" / "pyinstaller.exe"
    
    if venv_pyi.exists():
        pyinstaller = str(venv_pyi)
    elif venv_pyi_win.exists():
        pyinstaller = str(venv_pyi_win)
        
    if not pyinstaller:
        print("  pyinstaller not found. Installing via pip...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller", "pywebview"])
        pyinstaller = "pyinstaller"

    spec_file = ROOT / "HuaweiEMSManager.spec"
    run([pyinstaller, str(spec_file), "--noconfirm", "--clean"])


def create_platform_installer():
    log("4/4", f"Finalizing installer package for {SYSTEM}...")
    
    if SYSTEM == "Darwin":
        app_path = DIST / "Huawei EMS B1 Battery Manager.app"
        dmg_name = f"Huawei-EMS-B1-Battery-Manager-macOS-{platform.machine()}.dmg"
        dmg_path = DIST / dmg_name
        
        # Strip extended attributes and ad-hoc sign
        run(f'xattr -cr "{app_path}"')
        run(f'codesign --force --deep --sign - "{app_path}"')
        
        # Create DMG with Applications symlink
        staging = DIST / "dmg_staging"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        
        shutil.copytree(app_path, staging / app_path.name)
        os.symlink("/Applications", staging / "Applications")
        
        if dmg_path.exists():
            dmg_path.unlink()
            
        run(f'hdiutil create -volname "Huawei EMS B1 Battery Manager" -srcfolder "{staging}" -ov -format UDZO "{dmg_path}"')
        shutil.rmtree(staging, ignore_errors=True)
        
        print("\n" + "=" * 70)
        print(" macOS INSTALLER CREATED:")
        print(f" Application: {app_path}")
        print(f" DMG Package: {dmg_path}")
        print("=" * 70)

    elif SYSTEM == "Windows":
        iscc = shutil.which("ISCC.exe")
        iss_file = ROOT / "scripts" / "installer_windows.iss"
        if iscc and iss_file.exists():
            print("  Found Inno Setup Compiler. Compiling Setup installer (.exe)...")
            run([iscc, str(iss_file)])
            print(f"  Windows Setup Installer created in dist\\Huawei-EMS-B1-Manager-Windows-x64-Setup.exe")
        else:
            print("  Inno Setup (ISCC.exe) not found in PATH.")
            print(f"  Standalone application directory is ready at: dist\\HuaweiEMSManager\\")
            print("  To generate Windows Setup .exe: install Inno Setup and run 'ISCC scripts\\installer_windows.iss'")

    else:
        # Linux
        pkg_name = f"Huawei-EMS-B1-Manager-Linux-{platform.machine()}"
        stage_dir = DIST / pkg_name
        shutil.rmtree(stage_dir, ignore_errors=True)
        stage_dir.mkdir(parents=True, exist_ok=True)
        
        src_dir = DIST / "HuaweiEMSManager"
        shutil.copytree(src_dir, stage_dir, dirs_exist_ok=True)
        
        (stage_dir / "assets").mkdir(exist_ok=True)
        if (ASSETS / "icon.png").exists():
            shutil.copy(ASSETS / "icon.png", stage_dir / "assets" / "icon.png")
            
        shutil.copy(ROOT / "scripts" / "install_linux.sh", stage_dir / "install.sh")
        shutil.copy(ROOT / "scripts" / "huawei-ems-manager.desktop", stage_dir)
        (stage_dir / "install.sh").chmod(0o755)
        (stage_dir / "HuaweiEMSManager").chmod(0o755)
        
        tar_path = DIST / f"{pkg_name}.tar.gz"
        run(f'tar -czvf "{tar_path}" "{pkg_name}"', cwd=DIST)
        
        print("\n" + "=" * 70)
        print(" LINUX INSTALLER PACKAGE CREATED:")
        print(f" Archive: {tar_path}")
        print(" To install: unpack tar.gz and run 'sudo ./install.sh'")
        print("=" * 70)


def main():
    print("=" * 70)
    print(" Huawei EMS B1 Battery Manager - Standalone Installer Builder")
    print(f" Target Platform: {SYSTEM} ({platform.machine()})")
    print("=" * 70)

    check_prerequisites()
    build_frontend()
    package_executable()
    create_platform_installer()


if __name__ == "__main__":
    main()
