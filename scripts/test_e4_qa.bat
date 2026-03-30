@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0test_e4_qa.ps1" %*
exit /b %errorlevel%
