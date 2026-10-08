@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
  echo 관리자 권한으로 실행해야 합니다. (마우스 오른쪽 버튼 - 관리자 권한으로 실행)
  pause
  exit /b 1
)
schtasks /End /TN "WelderServer" >nul 2>&1
schtasks /Delete /TN "WelderServer" /F
netsh advfirewall firewall delete rule name="WelderServer" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq server_run*" >nul 2>&1
echo.
echo 자동 실행을 해제했습니다. (이미 떠 있는 서버는 PC 를 다시 시작하면 사라집니다)
pause
