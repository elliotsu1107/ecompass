@echo off
setlocal
cd /d "%~dp0"
set "BACKUP_DIR=%~dp0..\ecompass-backup\data"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
robocopy "%~dp0data" "%BACKUP_DIR%" /E /R:2 /W:2
exit /b %ERRORLEVEL%
