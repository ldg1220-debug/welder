@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 서버 자동 실행 등록

rem --- 관리자 권한 확인 ---
net session >nul 2>&1
if errorlevel 1 (
  echo [안내] 관리자 권한이 필요합니다.
  echo   이 파일을 마우스 오른쪽 버튼으로 눌러 "관리자 권한으로 실행" 을 선택하세요.
  pause
  exit /b 1
)

rem --- 필수 파일 / 마스터 계정 확인 ---
if not exist "%~dp0server.js" (
  echo [오류] server.js 가 이 폴더에 없습니다. server.js, welder-cert.html 과 같은 폴더에서 실행하세요.
  pause
  exit /b 1
)
if not exist "%~dp0data\users.json" (
  echo [안내] 아직 마스터 계정이 없습니다.
  echo   먼저 "서버_시작.bat" 를 한 번 실행해 마스터 아이디/비밀번호를 만든 뒤 Ctrl+C 로 끄고,
  echo   이 파일을 다시 실행하세요.
  pause
  exit /b 1
)

rem --- Node.js 위치 찾기 ---
set "NODE="
for /f "delims=" %%i in ('where node 2^>nul') do if not defined NODE set "NODE=%%i"
if not defined NODE (
  echo [오류] Node.js 를 찾을 수 없습니다. https://nodejs.org 에서 LTS 버전을 설치한 뒤 다시 실행하세요.
  pause
  exit /b 1
)
echo Node.js: %NODE%
echo %NODE% | findstr /i "\\Users\\" >nul
if not errorlevel 1 (
  echo [경고] Node.js 가 사용자 폴더 안에 설치돼 있어, 로그인 전에 자동 실행하는 방식이 동작하지 않을 수 있습니다.
  echo        가능하면 nodejs.org 설치 프로그램으로 시스템 전체(C:\Program Files\nodejs)에 설치하세요.
)

set "PORT=8080"
set /p PORT=포트 번호 (그냥 Enter = 8080):
if "%PORT%"=="" set "PORT=8080"

rem --- 실행용 파일 만들기 (서버가 꺼지면 10초 뒤 자동으로 다시 시작) ---
set "RUN=%~dp0server_run.bat"
> "%RUN%" echo @echo off
>> "%RUN%" echo cd /d "%~dp0"
>> "%RUN%" echo if not exist data mkdir data
>> "%RUN%" echo :loop
>> "%RUN%" echo "%NODE%" server.js --port %PORT% ^>^> data\server.log 2^>^&1
>> "%RUN%" echo ping -n 11 127.0.0.1 ^>nul
>> "%RUN%" echo goto loop

rem --- 작업 스케줄러 등록: 컴퓨터가 켜지면(로그인 전에도) 자동 실행, 창 없이 백그라운드 ---
schtasks /End /TN "WelderServer" >nul 2>&1
schtasks /Create /TN "WelderServer" /TR "\"%RUN%\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
if errorlevel 1 (
  echo [오류] 작업 스케줄러 등록에 실패했습니다.
  pause
  exit /b 1
)

rem --- 방화벽: 다른 PC 에서 접속 허용 ---
netsh advfirewall firewall delete rule name="WelderServer" >nul 2>&1
netsh advfirewall firewall add rule name="WelderServer" dir=in action=allow protocol=TCP localport=%PORT% >nul
echo 방화벽: TCP %PORT% 포트 허용

rem --- 절전 방지 (절전 모드가 되면 서버가 멈춥니다) ---
set "YN=Y"
set /p YN=전원 연결 시 절전/최대 절전 모드를 끌까요? [Y/n]:
if /i not "%YN%"=="n" (
  powercfg /change standby-timeout-ac 0
  powercfg /change hibernate-timeout-ac 0
  echo 절전 모드 해제 (전원 연결 시)
)

rem --- 지금 바로 시작 ---
schtasks /Run /TN "WelderServer" >nul
echo.
echo ============================================================
echo  등록 완료. 이제 이 PC 를 켜면 로그인하지 않아도 서버가 자동 실행됩니다.
echo  주소:  http://localhost:%PORT%   (다른 PC 는 http://이 PC의IP:%PORT%)
echo  로그:  %~dp0data\server.log
echo  해제:  자동실행_해제.bat 를 관리자 권한으로 실행
echo ============================================================
timeout /t 5 >nul
start "" "http://localhost:%PORT%"
pause
