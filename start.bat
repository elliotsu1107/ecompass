@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0ecompass.exe" (
  "%~dp0ecompass.exe"
  exit /b %ERRORLEVEL%
)
if not exist ".venv\Scripts\python.exe" (
  echo Missing ecompass.exe and .venv. Build the portable package or run: py -m venv .venv
  exit /b 1
)
.venv\Scripts\python.exe run.py
