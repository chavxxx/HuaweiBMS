#!/usr/bin/env bash
# ==============================================================================
# Build Standalone Linux Package for Huawei EMS B1 Battery Manager
# Compiles frontend, packages standalone PyInstaller binary, and builds tar.gz
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "======================================================================"
echo " Building Standalone Linux Distribution for Huawei EMS B1 Manager"
echo "======================================================================"

echo "[1/4] Building production React frontend..."
cd "${PROJECT_ROOT}/frontend"
npm install
npm run build
cd "${PROJECT_ROOT}"

echo "[2/4] Setting up Python virtual environment..."
if [ ! -d "backend/venv" ]; then
  python3 -m venv backend/venv
fi
backend/venv/bin/pip install --upgrade pip
backend/venv/bin/pip install -r backend/requirements.txt
backend/venv/bin/pip install pyinstaller

echo "[3/4] Compiling standalone Linux binary bundle with PyInstaller..."
backend/venv/bin/pyinstaller HuaweiEMSManager.spec --noconfirm --clean

echo "[4/4] Creating distribution archive and installer bundle..."
DIST_DIR="${PROJECT_ROOT}/dist"
PKG_NAME="Huawei-EMS-B1-Manager-Linux-x86_64"
STAGE_DIR="${DIST_DIR}/${PKG_NAME}"

rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

cp -r "${DIST_DIR}/HuaweiEMSManager/"* "${STAGE_DIR}/"
mkdir -p "${STAGE_DIR}/assets"
cp "${PROJECT_ROOT}/assets/icon.png" "${STAGE_DIR}/assets/" 2>/dev/null || true
cp "${PROJECT_ROOT}/scripts/install_linux.sh" "${STAGE_DIR}/install.sh"
cp "${PROJECT_ROOT}/scripts/huawei-ems-manager.desktop" "${STAGE_DIR}/"
cp "${PROJECT_ROOT}/README.md" "${STAGE_DIR}/"
chmod +x "${STAGE_DIR}/install.sh"
chmod +x "${STAGE_DIR}/HuaweiEMSManager"

cd "${DIST_DIR}"
tar -czvf "${PKG_NAME}.tar.gz" "${PKG_NAME}"

echo ""
echo "======================================================================"
echo " Linux Distribution Build Complete!"
echo " Artifact: dist/${PKG_NAME}.tar.gz"
echo " To install on Linux: unpack and run 'sudo ./install.sh'"
echo "======================================================================"
