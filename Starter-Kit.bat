@echo off
title VEXOR Starter Kit
cd /d "%~dp0"
echo ======================================================
echo   VEXOR Starter Kit - the best free tools for beginners
echo ======================================================
echo This installs: Git, VS Code, GitHub CLI, PowerToys, LocalSend
echo and downloads the "first-contributions" practice repo.
echo Close this window now if you don't want that.
pause

call :install Git.Git "Git (the engine behind GitHub)"
call :install Microsoft.VisualStudioCode "VS Code (code editor)"
call :install GitHub.cli "GitHub CLI (gh)"
call :install Microsoft.PowerToys "PowerToys (Windows power tools)"
call :install LocalSend.LocalSend "LocalSend (phone <-> PC file sharing)"

REM ---- practice repo ----
set "GH=%USERPROFILE%\Documents\GitHub"
if not exist "%GH%" mkdir "%GH%"
set "GIT=git"
where git >nul 2>nul || set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if exist "%GH%\first-contributions" (
  echo Practice repo already downloaded.
) else (
  echo Downloading the first-contributions practice repo...
  "%GIT%" clone --depth 1 https://github.com/firstcontributions/first-contributions.git "%GH%\first-contributions"
)

REM ---- open the best learning pages ----
start "" "https://github.com/firstcontributions/first-contributions"
start "" "https://roadmap.sh"
start "" "https://github.com/practical-tutorials/project-based-learning"

echo.
echo ======================================================
echo  Done! Your browser opened 3 learning pages.
echo  Start with first-contributions: follow its steps.
echo  Tip: in VEXOR type "learn" to see these again.
echo ======================================================
pause
exit /b

:install
echo.
echo Installing %~2 ...
winget install --id %1 -e --accept-package-agreements --accept-source-agreements
if errorlevel 1 echo    (Skipped or already installed: %~2)
exit /b
