@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Welder server - auto start remove
call :main
echo.
echo (Press any key to close this window)
pause >nul
exit /b

:main
net session >nul 2>&1
if errorlevel 1 goto :noadmin
schtasks /End /TN "WelderServer" >nul 2>&1
schtasks /Delete /TN "WelderServer" /F
netsh advfirewall firewall delete rule name="WelderServer" >nul 2>&1
echo.
echo Auto start removed. A server that is already running stops when you restart the PC
echo (or end node.exe in Task Manager).
goto :eof

:noadmin
echo [ERROR] Run this file as administrator (right-click - Run as administrator).
goto :eof
