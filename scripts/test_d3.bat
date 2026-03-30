@echo off
setlocal
set ROOT=%~dp0..
set ROOT=%ROOT:\/=%
powershell -ExecutionPolicy Bypass -File "%~dp0test_d3.ps1" %*
exit /b %errorlevel%
