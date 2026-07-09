@echo off
setlocal
cd /d "%~dp0"
set LOGFILE=%~dp0launch.log
"%~dp0venv\Scripts\pythonw.exe" "%~dp0launch.py" >> "%LOGFILE%" 2>&1
endlocal
