@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo =======================================================
echo AEBM - Installation environnement
echo =======================================================

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creation du venv...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 (
    python -m venv .venv
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [ERREUR] Impossible de creer .venv
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip

if exist "requirements.lock" (
  echo [INFO] Installation depuis requirements.lock ...
  python -m pip install -r requirements.lock
) else (
  echo [INFO] Installation depuis requirements.txt ...
  python -m pip install -r requirements.txt
)

if errorlevel 1 (
  echo [ERREUR] Installation echouee.
  exit /b 1
)

echo [OK] Installation terminee.
python scripts\preflight.py --quick
exit /b %errorlevel%
