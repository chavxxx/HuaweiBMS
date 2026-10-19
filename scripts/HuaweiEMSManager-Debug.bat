@echo off
title Huawei EMS B1 Battery Manager (Diagnostic Console)
cd /d "%~dp0"
echo ==============================================================================
echo  Huawei EMS B1 Battery Manager - Diagnostic Console Launcher
echo ==============================================================================
echo  Executable: %~dp0HuaweiEMSManager.exe
echo  Log Path:   %LOCALAPPDATA%\HuaweiEMSManager\logs\desktop.log
echo  Starting application backend on http://127.0.0.1:8000 ...
echo ==============================================================================
echo.

HuaweiEMSManager.exe %*

set EXIT_CODE=%ERRORLEVEL%
echo.
echo ==============================================================================
echo  Application terminated with exit code %EXIT_CODE%.
if %EXIT_CODE% NEQ 0 (
    echo.
    echo  Recent Diagnostic Log Output:
    if exist "%LOCALAPPDATA%\HuaweiEMSManager\logs\desktop.log" (
        powershell -NoProfile -Command "Get-Content -Path '$env:LOCALAPPDATA\HuaweiEMSManager\logs\desktop.log' -Tail 30"
    ) else (
        echo  No desktop.log file found in %LOCALAPPDATA%\HuaweiEMSManager\logs\
    )
)
echo ==============================================================================
pause
