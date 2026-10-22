@echo off
setlocal
cd /d "%~dp0"
title Uninstall State Issue Windows Service

net session >nul 2>nul
if errorlevel 1 (
  echo This uninstaller needs administrator permission.
  echo Right-click UNINSTALL_STATE_ISSUE_SERVICE.bat and choose "Run as administrator".
  pause
  exit /b 1
)

set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
  echo Python was not found. Remove the State Issue Server service using Windows Services.
  pause
  exit /b 1
)

sc.exe stop StateIssueServer >nul 2>nul
%PYTHON% windows_service.py remove
if errorlevel 1 (
  echo Service removal failed. Check that the service is stopped and pywin32 is installed.
  pause
  exit /b 1
)

echo State Issue Server was removed. The database and backups have not been deleted.
pause
exit /b 0
