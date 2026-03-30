@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_d5_stability.ps1" %*
exit /b %errorlevel%
