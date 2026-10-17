#!/usr/bin/env bash
# ==============================================================================
# Build Standalone macOS DMG and Application Bundle for Huawei EMS B1 Manager
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "======================================================================"
echo " Building Standalone macOS Distribution for Huawei EMS B1 Manager"
echo "======================================================================"

echo "[1/4] Building production React frontend..."
cd "${PROJECT_ROOT}/frontend"
npm install
npm run build
cd "${PROJECT_ROOT}"

echo "[2/4] Verifying macOS icon assets..."
if [ ! -f "assets/HuaweiEMS.icns" ]; then
  mkdir -p assets/HuaweiEMS.iconset
  sips -z 16 16     frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_16x16.png
  sips -z 32 32     frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_16x16@2x.png
  sips -z 32 32     frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_32x32.png
  sips -z 64 64     frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_32x32@2x.png
  sips -z 128 128   frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_128x128.png
  sips -z 256 256   frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_128x128@2x.png
  sips -z 256 256   frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_256x256.png
  sips -z 512 512   frontend/src/assets/hero.png --out assets/HuaweiEMS.iconset/icon_256x256@2x.png
  iconutil -c icns assets/HuaweiEMS.iconset -o assets/HuaweiEMS.icns
  cp assets/HuaweiEMS.iconset/icon_256x256.png assets/icon.png
fi

echo "[3/4] Compiling macOS Application Bundle (.app) with PyInstaller..."
if [ -f "${PROJECT_ROOT}/backend/venv/bin/pyinstaller" ]; then
  PYI="${PROJECT_ROOT}/backend/venv/bin/pyinstaller"
else
  PYI="pyinstaller"
fi
"${PYI}" HuaweiEMSManager.spec --noconfirm --clean

APP_PATH="${PROJECT_ROOT}/dist/Huawei EMS B1 Battery Manager.app"
echo "Cleaning extended attributes and ad-hoc signing..."
xattr -cr "${APP_PATH}"
codesign --force --deep --sign - "${APP_PATH}"

echo "[4/4] Generating Apple Disk Image (.dmg) Installer..."
ARCH="$(uname -m)"
DMG_PATH="${PROJECT_ROOT}/dist/Huawei-EMS-B1-Battery-Manager-macOS-${ARCH}.dmg"
rm -f "${DMG_PATH}"

# Prepare DMG staging folder with Applications shortcut
STAGING="${PROJECT_ROOT}/dist/dmg_staging"
rm -rf "${STAGING}"
mkdir -p "${STAGING}"
cp -r "${APP_PATH}" "${STAGING}/"
ln -s /Applications "${STAGING}/Applications"

hdiutil create -volname "Huawei EMS B1 Battery Manager" -srcfolder "${STAGING}" -ov -format UDZO "${DMG_PATH}"
rm -rf "${STAGING}"

echo ""
echo "======================================================================"
echo " macOS Standalone Installer Build Complete!"
echo " - Application Bundle: ${APP_PATH}"
echo " - DMG Installer:      ${DMG_PATH}"
echo "======================================================================"
