@echo off
setlocal
cd /d "%~dp0"
title Update State Issue

net session >nul 2>nul
if errorlevel 1 (
  echo This updater needs administrator permission.
  echo Right-click UPDATE_STATE_ISSUE.bat and choose "Run as administrator".
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

echo Checking for a published State Issue update...
%PYTHON% update_state_issue.py
if errorlevel 1 (
  echo.
  echo Update did not complete. Read the message above before trying again.
  pause
  exit /b 1
)

echo.
echo State Issue update completed successfully.
pause
exit /b 0
