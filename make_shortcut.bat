@echo off
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1"
echo.
echo (Press any key to close this window)
pause >nul
