@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_e3_dryrun.ps1" %*
exit /b %errorlevel%
