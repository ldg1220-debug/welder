@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Welder server - auto start setup
call :main
echo.
echo (Press any key to close this window)
pause >nul
exit /b

:main
net session >nul 2>&1
if errorlevel 1 goto :noadmin
if not exist "%~dp0server.js" goto :nojs
if not exist "%~dp0data\users.json" goto :nomaster

set "NODE="
for /f "delims=" %%i in ('where node 2^>nul') do if not defined NODE set "NODE=%%i"
if not defined NODE goto :nonode
echo Node.js: %NODE%
echo %NODE% | findstr /i "\\Users\\" >nul
if not errorlevel 1 echo [WARNING] Node.js is installed inside a user folder. Auto start before login may fail. Install Node.js for all users (C:\Program Files\nodejs).

set "PORT=8080"
set /p PORT=Port number (just press Enter for 8080):
if "%PORT%"=="" set "PORT=8080"

set "RUN=%~dp0server_run.bat"
> "%RUN%" echo @echo off
>> "%RUN%" echo cd /d "%%~dp0"
>> "%RUN%" echo if not exist data mkdir data
>> "%RUN%" echo :loop
>> "%RUN%" echo "%NODE%" server.js --port %PORT% ^>^> data\server.log 2^>^&1
>> "%RUN%" echo ping -n 11 127.0.0.1 ^>nul
>> "%RUN%" echo goto loop

schtasks /End /TN "WelderServer" >nul 2>&1
schtasks /Create /TN "WelderServer" /TR "\"%RUN%\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if errorlevel 1 goto :taskfail

netsh advfirewall firewall delete rule name="WelderServer" >nul 2>&1
netsh advfirewall firewall add rule name="WelderServer" dir=in action=allow protocol=TCP localport=%PORT% >nul
echo Firewall: TCP port %PORT% allowed.

set "YN=Y"
set /p YN=Disable sleep/hibernate while plugged in? [Y/n]:
if /i "%YN%"=="n" goto :skipsleep
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
echo Sleep/hibernate disabled (plugged in).
:skipsleep

schtasks /Run /TN "WelderServer" >nul
echo.
echo ============================================================
echo  DONE. The server now starts automatically when this PC boots
echo  (no login needed, runs in background).
echo  Address : http://localhost:%PORT%   (other PCs: http://THIS-PC-IP:%PORT%)
echo  Log     : %~dp0data\server.log
echo  Remove  : run "auto_start_remove.bat" as administrator
echo ============================================================
timeout /t 5 >nul
start "" "http://localhost:%PORT%"
goto :eof

:noadmin
echo [ERROR] Administrator rights are required.
echo  Right-click this file and choose "Run as administrator".
goto :eof
:nojs
echo [ERROR] server.js was not found in this folder: %~dp0
echo  Run this file from the folder that contains server.js and welder-cert.html.
goto :eof
:nomaster
echo [ERROR] No master account yet (data\users.json not found).
echo  1) Run "server_start.bat" (or: node server.js) once and create the master ID/password
echo  2) Stop it with Ctrl+C, then run this file again as administrator.
goto :eof
:nonode
echo [ERROR] Node.js was not found. Install the LTS version from https://nodejs.org and run this again.
goto :eof
:taskfail
echo [ERROR] Could not register the scheduled task.
goto :eof
