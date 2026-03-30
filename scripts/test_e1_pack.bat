@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_e1_pack.ps1" %*
exit /b %errorlevel%
