@echo off
setlocal
rem Run from this folder even if the shortcut was launched elsewhere.
cd /d "%~dp0"
title State Issue Server
set "PYTHON="
rem Prefer the Windows Python launcher, then fall back to python on PATH.
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
  echo Python was not found. Run SETUP_NEW_COMPUTER.bat first.
  pause
  exit /b 1
)
set /a FAILURES=0
:RUN
rem A clean Ctrl+C exit is not restarted; crashes get up to five retries.
%PYTHON% server.py
set "EXITCODE=%ERRORLEVEL%"
if "%EXITCODE%"=="0" goto STOPPED
set /a FAILURES+=1
echo.
echo State Issue stopped unexpectedly with exit code %EXITCODE%.
if %FAILURES% GEQ 5 goto FAILED
echo Restarting in 3 seconds. Consecutive failed starts: %FAILURES% of 5.
timeout /t 3 /nobreak >nul
goto RUN
:FAILED
echo State Issue failed 5 times in a row and will not restart again automatically.
echo Write down the error shown above and contact the program support person.
pause
exit /b 1
:STOPPED
echo State Issue has stopped.
exit /b 0
