@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

if /I "%~1"=="cov" (
  if "%~2"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\test_d1.ps1" -Coverage -MinCoverage 20
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\test_d1.ps1" -Coverage -MinCoverage %~2
  )
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\test_d1.ps1"
)

exit /b %errorlevel%
