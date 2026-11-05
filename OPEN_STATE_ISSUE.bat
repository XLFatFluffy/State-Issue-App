@echo off
setlocal
rem Connect workstations to the host's reserved private-network IP.
set "STATE_ISSUE_ADDRESS=http://10.9.50.171:8787/"
start "State Issue" "%STATE_ISSUE_ADDRESS%"
