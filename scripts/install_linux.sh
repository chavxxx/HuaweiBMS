#!/usr/bin/env bash
# ==============================================================================
# Linux Standalone Installer for Huawei EMS B1 Battery Manager
# Installs application to /opt/huawei-ems-manager, creates symlinks, and sets up
# serial USB-to-RS485 dialout user permissions.
# ==============================================================================

set -e

APP_NAME="Huawei EMS B1 Battery Manager"
INSTALL_DIR="/opt/huawei-ems-manager"
BIN_LINK="/usr/local/bin/huawei-ems-manager"
DESKTOP_FILE="/usr/share/applications/huawei-ems-manager.desktop"

echo "======================================================================"
echo " Installing $APP_NAME for Linux"
echo "======================================================================"

if [ "$EUID" -ne 0 ]; then
  echo "This installer requires administrative privileges. Requesting sudo..."
  exec sudo bash "$0" "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_SRC="${SCRIPT_DIR}/../dist/HuaweiEMSManager"

if [ ! -d "$DIST_SRC" ]; then
  if [ -d "${SCRIPT_DIR}/HuaweiEMSManager" ]; then
    DIST_SRC="${SCRIPT_DIR}/HuaweiEMSManager"
  else
    echo "ERROR: Compiled binary package directory 'HuaweiEMSManager' not found."
    echo "Please run './scripts/build_linux_installer.sh' first."
    exit 1
  fi
fi

echo "[1/4] Copying files to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
cp -r "${DIST_SRC}/"* "${INSTALL_DIR}/"
mkdir -p "${INSTALL_DIR}/assets"
if [ -f "${SCRIPT_DIR}/../assets/icon.png" ]; then
  cp "${SCRIPT_DIR}/../assets/icon.png" "${INSTALL_DIR}/assets/icon.png"
fi

echo "[2/4] Creating executable symlink at ${BIN_LINK}..."
chmod +x "${INSTALL_DIR}/HuaweiEMSManager"
ln -sf "${INSTALL_DIR}/HuaweiEMSManager" "${BIN_LINK}"

echo "[3/4] Installing Desktop Application Menu Entry..."
if [ -f "${SCRIPT_DIR}/huawei-ems-manager.desktop" ]; then
  cp "${SCRIPT_DIR}/huawei-ems-manager.desktop" "${DESKTOP_FILE}"
  chmod 644 "${DESKTOP_FILE}"
fi

echo "[4/4] Configuring USB-to-RS485 serial permissions..."
# Add current login user to dialout group so RS485 adapters (/dev/ttyUSB*) can be opened without root
REAL_USER="${SUDO_USER:-$USER}"
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
  if getent group dialout > /dev/null 2>&1; then
    usermod -a -G dialout "$REAL_USER"
    echo "  Added user '$REAL_USER' to 'dialout' group."
  elif getent group uucp > /dev/null 2>&1; then
    usermod -a -G uucp "$REAL_USER"
    echo "  Added user '$REAL_USER' to 'uucp' group."
  fi
fi

# Optional udev rule for FTDI & CH340 RS485 adapters
UDEV_RULE_FILE="/etc/udev/rules.d/99-huawei-ems-rs485.rules"
cat << 'EOF' > "${UDEV_RULE_FILE}"
# Huawei EMS RS485 Serial Adapters (FTDI, CH340, CP210x, PL2303)
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0666", GROUP="dialout"
EOF

udevadm control --reload-rules || true
udevadm trigger || true

echo ""
echo "======================================================================"
echo " $APP_NAME installed successfully!"
echo " - Run from application menu or terminal command: huawei-ems-manager"
echo " - Installed location: ${INSTALL_DIR}"
echo " Note: If this is the first time setting up serial ports, log out and"
echo " back in for dialout group permissions to take full effect."
echo "======================================================================"
