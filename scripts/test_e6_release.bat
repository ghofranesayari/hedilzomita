@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_e6_release.ps1" %*
exit /b %ERRORLEVEL%
