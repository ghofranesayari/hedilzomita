@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_e5_bundle.ps1" %*
exit /b %ERRORLEVEL%
