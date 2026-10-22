@echo off
setlocal
cd /d "%~dp0"
title Install State Issue Windows Service

net session >nul 2>nul
if errorlevel 1 (
  echo This installer needs administrator permission.
  echo Right-click INSTALL_STATE_ISSUE_SERVICE.bat and choose "Run as administrator".
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

echo Installing the Windows service dependency (pywin32)...
%PYTHON% -m pip install pywin32
if errorlevel 1 (
  echo Could not install pywin32. Check internet access and Python, then retry.
  pause
  exit /b 1
)

echo Registering State Issue Server to start automatically with Windows...
%PYTHON% windows_service.py --startup auto install
if errorlevel 1 (
  echo Service registration failed. Check that pywin32 installed correctly.
  pause
  exit /b 1
)

sc.exe config StateIssueServer start= delayed-auto
if errorlevel 1 goto CONFIGERROR
sc.exe failure StateIssueServer reset= 86400 actions= restart/5000/restart/15000/restart/30000
if errorlevel 1 goto CONFIGERROR
sc.exe failureflag StateIssueServer 1
if errorlevel 1 goto CONFIGERROR

echo Starting State Issue Server...
sc.exe start StateIssueServer
if errorlevel 1 (
  echo The service was installed, but did not start. Check Windows Event Viewer.
  pause
  exit /b 1
)

echo.
echo State Issue Server is installed and configured to start with Windows.
echo Use START_STATE_ISSUE.bat to open the app on this computer.
pause
exit /b 0

:CONFIGERROR
echo Service recovery configuration failed. The service was registered but may not restart after a failure.
echo Run this installer again as administrator after resolving the error.
pause
exit /b 1
