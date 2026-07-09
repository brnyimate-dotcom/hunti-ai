@echo off
setlocal
cd /d "%~dp0"
if not exist release mkdir release
"%~dp0venv\Scripts\pyinstaller.exe" --clean --noconfirm --onedir --windowed --distpath "%~dp0release" --workpath "%~dp0build" --specpath "%~dp0" --name HuntiAI main.py
endlocal
