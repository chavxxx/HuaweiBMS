@echo off
title Huawei EMS B1 Battery Manager (Diagnostic Console)
cd /d "%~dp0"
echo ==============================================================================
echo  Huawei EMS B1 Battery Manager - Diagnostic Console Launcher
echo ==============================================================================
echo  Starting application backend on http://127.0.0.1:8000 ...
echo  If an error occurs, the window will remain open so you can view the logs.
echo ==============================================================================
echo.

HuaweiEMSManager.exe

echo.
echo ==============================================================================
echo  Application terminated with exit code %ERRORLEVEL%.
echo ==============================================================================
pause
