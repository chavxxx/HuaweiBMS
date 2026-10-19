@echo off
REM ==============================================================================
REM Build script for Huawei EMS B1 Battery Manager on Windows
REM Produces standalone executable and Inno Setup installer (.exe)
REM ==============================================================================

echo [1/4] Checking Python environment...
python --version
if errorlevel 1 (
    echo ERROR: Python 3 is not installed or not in PATH.
    pause
    exit /b 1
)

echo [2/4] Building production React frontend...
cd frontend
call npm install
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed.
    pause
    exit /b 1
)
cd ..

echo [3/4] Installing backend packaging dependencies...
python -m pip install -r backend/requirements.txt
python -m pip install pyinstaller pywebview pillow pythonnet pywin32

echo [4/4] Compiling standalone Windows executable with PyInstaller...
python -m PyInstaller HuaweiEMSManager.spec --noconfirm --clean
if errorlevel 1 (
    echo ERROR: PyInstaller compilation failed.
    pause
    exit /b 1
)
copy scripts\HuaweiEMSManager-Debug.bat dist\HuaweiEMSManager\
python -c "import shutil, os, glob, webview; lib_dir=os.path.join(os.path.dirname(webview.__file__), 'lib'); [shutil.copy(f, 'dist/HuaweiEMSManager') for f in glob.glob(os.path.join(lib_dir, '*.dll'))]; [shutil.copy(f, 'dist/HuaweiEMSManager/_internal') for f in glob.glob(os.path.join(lib_dir, '*.dll')) if os.path.exists('dist/HuaweiEMSManager/_internal')]; native_dlls=glob.glob(os.path.join(lib_dir, 'runtimes', 'win-x64', 'native', '*.dll')); [shutil.copy(f, 'dist/HuaweiEMSManager') for f in native_dlls]; [shutil.copy(f, 'dist/HuaweiEMSManager/_internal') for f in native_dlls if os.path.exists('dist/HuaweiEMSManager/_internal')]"

echo.
echo ==============================================================================
echo Build completed successfully!
echo Standalone binary available in: dist\HuaweiEMSManager\HuaweiEMSManager.exe
echo.
echo To compile the Setup Installer (.exe):
echo Run Inno Setup Compiler (ISCC.exe) on scripts\installer_windows.iss
echo ==============================================================================
