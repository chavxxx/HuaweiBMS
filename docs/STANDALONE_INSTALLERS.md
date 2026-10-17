# Multi-Platform Standalone Installer Guide

This guide explains how to install and build standalone distributions of **Huawei EMS B1 Battery Manager** across **macOS**, **Windows**, and **Linux**.

The standalone packages include the complete Python backend, serial communication service, PySerial engine, embedded register databases, and the compiled React production UI. **No manual installation of Python, Node.js, npm, or terminal commands is required by the end-user.**

---

## 1. Quick Installation by Platform

### A. macOS (`.dmg` Installer)

1. Download **`Huawei-EMS-B1-Battery-Manager-macOS-arm64.dmg`** (Apple Silicon) or Intel x64 package.
2. Double-click the `.dmg` disk image.
3. Drag **`Huawei EMS B1 Battery Manager.app`** into your **`Applications`** folder.
4. Plug in your USB-to-RS485 adapter (e.g. FTDI FT232R) connected to the battery's RJ45 COM port.
5. Launch the application from Launchpad or `/Applications`.
   - The application opens directly in a dedicated desktop window powered by native macOS WebKit.
   - The serial port `/dev/cu.usbserial-*` is auto-detected.

---

### B. Windows (`.exe` Setup Wizard & Portable Zip)

1. **Setup Wizard (`.exe`):**
   - Download and run **`Huawei-EMS-B1-Manager-Windows-x64-Setup.exe`**.
   - Follow the modern setup wizard.
   - Installs to `C:\Program Files\Huawei EMS B1 Battery Manager` with desktop and Start Menu shortcuts.
2. **Portable Version (`.zip`):**
   - Download **`Huawei-EMS-B1-Manager-Windows-x64-Portable.zip`**.
   - Extract to any folder or USB flash drive.
   - Double-click **`HuaweiEMSManager.exe`**.
   - Uses Microsoft Edge WebView2 for native desktop rendering.

*Note for Windows users:* Plug in your USB-to-RS485 adapter and ensure the FTDI/CH340 VCP driver is installed (Windows Update installs this automatically). Your adapter will appear as `COM3`, `COM4`, etc.

---

### C. Linux (`.tar.gz` + Automated System Installer)

1. Download **`Huawei-EMS-B1-Manager-Linux-x86_64.tar.gz`**.
2. Unpack the archive:
   ```bash
   tar -xvf Huawei-EMS-B1-Manager-Linux-x86_64.tar.gz
   cd Huawei-EMS-B1-Manager-Linux-x86_64
   ```
3. Run the installer:
   ```bash
   sudo ./install.sh
   ```
4. What the Linux installer does:
   - Installs binary and resources into `/opt/huawei-ems-manager`.
   - Creates a global command at `/usr/local/bin/huawei-ems-manager`.
   - Installs desktop menu launcher `/usr/share/applications/huawei-ems-manager.desktop`.
   - Adds your user to the **`dialout`** group so you can access serial ports (`/dev/ttyUSB0`) without root.
   - Sets up `/etc/udev/rules.d/99-huawei-ems-rs485.rules` for USB-RS485 adapters.

---

## 2. Building Installers from Source

You can build the native installer on any operating system using our unified builder script:

### Universal One-Command Build (Cross-Platform)

```bash
python3 scripts/build_installer.py
```
*This command auto-detects your host operating system, compiles the React frontend bundle with Vite, and builds the native installer.*

### Platform-Specific Scripts

* **macOS DMG:**
  ```bash
  ./scripts/build_macos_installer.sh
  ```
  *Produces `dist/Huawei-EMS-B1-Battery-Manager-macOS-arm64.dmg`.*

* **Linux Package:**
  ```bash
  ./scripts/build_linux_installer.sh
  ```
  *Produces `dist/Huawei-EMS-B1-Manager-Linux-x86_64.tar.gz` with `install.sh`.*

* **Windows Setup Executable:**
  ```bat
  scripts\build_windows_installer.bat
  ```
  *Produces `dist\Huawei-EMS-B1-Manager-Windows-x64-Setup.exe` (requires Inno Setup).*

---

## 3. Automated Multi-Platform CI/CD (GitHub Actions)

A fully automated continuous integration pipeline is provided at:
[`.github/workflows/build-installers.yml`](file:///Users/chavxxx/Documents/Projects/huawei-ems-b1-manager/.github/workflows/build-installers.yml)

### How it works:
1. When you push a git tag (e.g. `git tag v1.0.0 && git push origin v1.0.0`), GitHub Actions automatically launches three parallel cloud runners:
   - `macos-14` (Apple Silicon) &rarr; Builds and uploads `.dmg`.
   - `windows-latest` &rarr; Builds and uploads `Setup.exe` and `Portable.zip`.
   - `ubuntu-22.04` &rarr; Builds and uploads `.tar.gz` and desktop installer.
2. The `release` job automatically collects all artifacts and creates a GitHub Release with downloadable installers.

---

## 4. Desktop Runner Options & CLI Flags

The standalone executable can also be launched with command-line flags:

```bash
# Launch in native desktop GUI window (default):
./HuaweiEMSManager

# Run as background server without desktop window (headless / server mode):
./HuaweiEMSManager --headless

# Run on custom port:
./HuaweiEMSManager --port 9000
```
