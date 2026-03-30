@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_d6_calibration.ps1" %*
exit /b %errorlevel%
