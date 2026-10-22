@echo off
setlocal
rem Replace this example with the address printed by the host server window.
set "STATE_ISSUE_ADDRESS=http://192.168.1.20:8787/"
start "State Issue" "%STATE_ISSUE_ADDRESS%"
