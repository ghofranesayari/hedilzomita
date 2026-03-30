@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_e2_checklist.ps1" %*
exit /b %errorlevel%
