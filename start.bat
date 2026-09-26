@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0ecompass.exe" (
  start "ecompass" "%~dp0ecompass.exe"
  goto open_browser
)
if not exist ".venv\Scripts\python.exe" (
  echo Missing ecompass.exe and .venv. Build the portable package or run: py -m venv .venv
  exit /b 1
)
start "ecompass" /b .venv\Scripts\python.exe run.py

:open_browser
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
exit /b 0
