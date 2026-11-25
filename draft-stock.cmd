@echo off
setlocal
call "%~dp0draft.cmd" --confirm-run --select-stock
exit /b %ERRORLEVEL%
