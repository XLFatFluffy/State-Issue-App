@echo off
setlocal
rem Run checks relative to this app folder so the program files are found.
cd /d "%~dp0"
title State Issue - First Time Setup

echo ==============================================
echo  STATE ISSUE - FIRST TIME SETUP
echo ==============================================
echo.
set "PYTHON="
rem Check for an existing Python before offering an installation.
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
  echo Python 3 was not found on this computer.
  where winget >nul 2>nul
  if not errorlevel 1 (
    echo Attempting to install Python 3.12 with Windows Package Manager.
    echo This step requires internet access and may request approval.
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (
      set "PYTHON=py -3"
      echo.
      echo If Python is still not detected below, close this window and run setup again.
    )
  )
)
if not defined PYTHON (
  rem Windows 7 cannot use current Python releases, so use its last supported one.
  echo Downloading Python 3.8.10 (the last version that runs on Windows 7).
  echo This needs an internet connection and can take a few minutes.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe' -OutFile '%TEMP%\python-setup.exe'"
  if exist "%TEMP%\python-setup.exe" (
    echo Installing Python (a few minutes)...
    "%TEMP%\python-setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    where py >nul 2>nul && set "PYTHON=py -3"
    if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
  )
)
if not defined PYTHON (
  echo.
  echo Automatic installation was unavailable or did not complete.
  echo Install Python yourself, then run this file again.
  echo On Windows 7, use Python 3.8.10 - it is the last version that runs there:
  echo   https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe
  echo On Windows 10 or 11, any current version works:
  echo   https://www.python.org/downloads/windows/
  echo Tick "Add python.exe to PATH" during the install, then run this file again.
  pause
  exit /b 1
)

echo Python check:
%PYTHON% --version
if errorlevel 1 goto PYERROR

echo.
rem Do not open the network port until the app's own tests have passed.
echo Checking required application files...
for %%F in (Stateissue.html server.py windows_service.py seed.json sw.js test_server.py) do (
  if not exist "%%F" (
    echo MISSING REQUIRED FILE: %%F
    pause
    exit /b 1
  )
)

echo.
echo Running automated checks...
%PYTHON% test_server.py
if errorlevel 1 goto TESTERROR

echo.
echo Attempting to open Windows Firewall port 8787 for private networks.
net session >nul 2>nul
if errorlevel 1 (
  echo Not running as administrator. Firewall rule was not changed.
  echo If other computers cannot connect, run this file as administrator.
) else (
  netsh advfirewall firewall add rule name="State Issue TCP 8787" dir=in action=allow protocol=TCP localport=8787 profile=private >nul
  if errorlevel 1 (echo Firewall rule could not be added. Check firewall settings.) else (echo Firewall rule is ready for private networks.)
)

echo.
echo Setup checks completed.
echo On the host computer, run INSTALL_STATE_ISSUE_SERVICE.bat as administrator.
pause
exit /b 0
:PYERROR
echo Python could not be started. Check the installation and PATH, then try again.
pause
exit /b 1
:TESTERROR
echo Automated checks failed. Do not use this package until the error is investigated.
pause
exit /b 1
