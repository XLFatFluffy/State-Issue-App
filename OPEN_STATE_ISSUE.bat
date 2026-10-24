@echo off
setlocal
rem Connect workstations to the State Issue host.
set "STATE_ISSUE_ADDRESS=http://25.34.230.125:8787/"
start "State Issue" "%STATE_ISSUE_ADDRESS%"
