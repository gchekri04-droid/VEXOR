@echo off
title KAIRO Setup
cd /d "%~dp0"
echo ============================================
echo   KAIRO setup - this may take 5-15 minutes
echo ============================================
echo.

REM ---- 1. Python ----
where py >nul 2>nul
if errorlevel 1 (
  echo [1/5] Python not found. Installing Python 3.12 with winget...
  winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
  echo.
  echo Python installed. CLOSE this window and double-click Setup-KAIRO.bat again.
  pause
  exit /b
)
echo [1/5] Python found.

REM ---- 2. Private Python environment for KAIRO ----
if not exist ".venv\Scripts\python.exe" (
  echo [2/5] Creating KAIRO's Python environment...
  py -3 -m venv .venv
)
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
echo [2/5] Installing voice packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" -m pip install pyaudio
if errorlevel 1 echo    (PyAudio failed - KAIRO will still speak, but the Talk button won't work.)

REM ---- 3. Ollama (free local AI brain) ----
where ollama >nul 2>nul
if errorlevel 1 (
  echo [3/5] Installing Ollama, KAIRO's free AI brain...
  winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
  echo.
  echo Ollama installed. CLOSE this window and double-click Setup-KAIRO.bat again.
  pause
  exit /b
)
echo [3/5] Ollama found.

REM ---- 4. Download the AI model (about 2 GB, one time) ----
echo [4/5] Downloading the AI model (about 2 GB, one time only)...
start "" /min ollama serve >nul 2>nul
timeout /t 3 >nul
ollama pull llama3.2

REM ---- 5. Desktop shortcut ----
echo [5/5] Creating desktop shortcut...
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\KAIRO.lnk'); $s.TargetPath='%~dp0Start-KAIRO.bat'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"

echo.
echo ============================================
echo   Done! Double-click KAIRO on your desktop.
echo ============================================
pause
