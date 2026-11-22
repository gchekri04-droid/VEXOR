@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run Setup-VEXOR.bat first.
  pause
  exit /b
)
REM make sure the AI brain is running (harmless if it already is)
where ollama >nul 2>nul && (start "" /min ollama serve >nul 2>nul)
start "" ".venv\Scripts\pythonw.exe" vexor.py
