@echo off
setlocal
cd /d "%~dp0"
title State Issue - Verify a Backup
echo ==============================================
echo  STATE ISSUE - VERIFY A BACKUP
echo ==============================================
echo.
echo This checks that a backup file is not damaged and can be read,
echo without changing anything. It is safe to run any time, as often
echo as you like, and does not touch your live data.
echo.

set "TARGET=%~1"
if not defined TARGET (
  echo Drag a backup file from the "backups" folder onto this icon and drop it,
  echo or type its full path below.
  echo Example: backups\daily_2026-10-19.db
  echo.
  set /p TARGET=Backup file to check: 
)
if not defined TARGET (
  echo No file given.
  pause
  exit /b 1
)

set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
  echo Python was not found. Run SETUP_NEW_COMPUTER.bat first.
  pause
  exit /b 1
)

%PYTHON% server.py --verify "%TARGET%"
echo.
if errorlevel 1 (
  echo This backup did NOT pass. Try an older backup from the backups folder,
  echo or contact the support person before relying on it.
) else (
  echo This backup is good. This is also the repeatable restore test mentioned
  echo in ADMIN_GUIDE.txt - running this on your most recent backup every so
  echo often confirms your backups are actually usable, without touching the
  echo live database.
)
pause
