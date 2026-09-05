@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run: py -m venv .venv
  echo Then run: .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)
.venv\Scripts\python.exe run.py
