@echo off
setlocal
rem Replace this example with the host computer's IPv4 address.
set "STATE_ISSUE_ADDRESS=http://192.168.1.20:8787/"
start "State Issue" "%STATE_ISSUE_ADDRESS%"
