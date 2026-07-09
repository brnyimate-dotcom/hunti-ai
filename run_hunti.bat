@echo off
setlocal
cd /d "%~dp0"
"%~dp0venv\Scripts\pythonw.exe" "%~dp0main.py"
endlocal
