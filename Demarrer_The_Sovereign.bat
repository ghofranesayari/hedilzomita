@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title The Sovereign - Demarrage
color 0B

echo =======================================================
echo     THE SOVEREIGN - DEMARRAGE AUTOMATIQUE
echo =======================================================
echo.

if not exist ".env" (
    echo [INFO] Fichier .env absent.
    if exist ".env.cloud.template" (
        copy /Y ".env.cloud.template" ".env" >nul
        echo [ACTION] Un .env template a ete cree.
        echo          Completez les valeurs Neo4j Cloud + Groq, enregistrez, puis relancez.
        start "" notepad ".env"
    ) else if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo [ACTION] Un .env a ete cree depuis .env.example.
        echo          Completez les valeurs, enregistrez, puis relancez.
        start "" notepad ".env"
    ) else (
        echo [ERREUR] Aucun .env ni .env.example trouve.
    )
    goto :end
)

set "TARGET_CONTAINER=neo4j-aebm"
set "NEO4J_USER=neo4j"
set "NEO4J_PASSWORD="
set "NEO4J_URI="
set "AEBM_NEO4J_MODE="
set "USE_CLOUD_NEO4J=0"
set "GROQ_API_KEY="

for /f "usebackq tokens=1,* delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\read_env_vars.ps1" -Path ".env"`) do (
    set "%%A=%%B"
)

if /I "%AEBM_NEO4J_MODE%"=="cloud" set "USE_CLOUD_NEO4J=1"
if defined NEO4J_URI (
    echo %NEO4J_URI% | findstr /I /B "neo4j+s://" >nul
    if not errorlevel 1 set "USE_CLOUD_NEO4J=1"
)

if "%USE_CLOUD_NEO4J%"=="1" (
    if not defined NEO4J_PASSWORD (
        echo [ERREUR] Mode cloud detecte mais NEO4J_PASSWORD est vide dans .env.
        echo          Ouvrez .env, completez les cles, puis relancez.
        start "" notepad ".env"
        goto :end
    )
    if not defined GROQ_API_KEY (
        rem GROQ_API_KEY is checked by preflight, keep flow.
    )
    echo [1/5] Mode Neo4j Cloud detecte.
    echo [OK] Docker non requis sur cette machine.
    echo.
) else (
    if not defined NEO4J_PASSWORD (
        set "NEO4J_PASSWORD=ChangeMe_12345"
        echo [WARN] NEO4J_PASSWORD non trouve dans .env.
        echo        Mot de passe temporaire utilise pour mode local Docker.
    )

    echo [1/5] Verification Docker Desktop...
    where docker >nul 2>nul
    if errorlevel 1 (
        echo [ERREUR] Docker n'est pas detecte.
        echo          Installez Docker Desktop ou passez en mode cloud dans .env.
        goto :end
    )

    docker info >nul 2>nul
    if errorlevel 1 (
        echo [ERREUR] Docker Desktop est installe mais non demarre.
        echo          Ouvrez Docker Desktop, attendez "Engine running", puis relancez.
        goto :end
    )
    echo [OK] Docker actif.
    echo.

    echo [2/5] Verification/creation Neo4j local...
    docker inspect "%TARGET_CONTAINER%" >nul 2>nul
    if errorlevel 1 (
        docker inspect "neo4j" >nul 2>nul
        if errorlevel 1 (
            echo [INFO] Conteneur Neo4j absent. Creation automatique...

            docker image inspect neo4j:5 >nul 2>nul
            if errorlevel 1 (
                echo [INFO] Telechargement image neo4j:5...
                docker pull neo4j:5
                if errorlevel 1 (
                    echo [ERREUR] Echec du telechargement neo4j:5.
                    goto :end
                )
            )

            docker run -d --name "%TARGET_CONTAINER%" -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=%NEO4J_USER%/%NEO4J_PASSWORD% neo4j:5 >nul 2>nul
            if errorlevel 1 (
                echo [ERREUR] Echec creation du conteneur "%TARGET_CONTAINER%".
                echo          Verifiez si les ports 7474/7687 sont deja utilises.
                goto :end
            )

            echo [OK] Conteneur "%TARGET_CONTAINER%" cree et demarre.
            timeout /t 7 /nobreak >nul
        ) else (
            set "TARGET_CONTAINER=neo4j"
            docker start "%TARGET_CONTAINER%" >nul 2>nul
            if errorlevel 1 (
                echo [ERREUR] Impossible de demarrer le conteneur "%TARGET_CONTAINER%".
                goto :end
            )
            echo [OK] Conteneur "%TARGET_CONTAINER%" demarre.
            timeout /t 5 /nobreak >nul
        )
    ) else (
        docker start "%TARGET_CONTAINER%" >nul 2>nul
        if errorlevel 1 (
            echo [ERREUR] Impossible de demarrer le conteneur "%TARGET_CONTAINER%".
            goto :end
        )
        echo [OK] Conteneur "%TARGET_CONTAINER%" demarre.
        timeout /t 5 /nobreak >nul
    )
    echo.
)

echo [3/5] Verification environnement Python...
if not exist ".\.venv\Scripts\activate.bat" (
    echo [INFO] .venv absent. Installation automatique...
    if exist ".\scripts\install_env.bat" (
        call ".\scripts\install_env.bat"
        if errorlevel 1 (
            echo [ERREUR] Echec installation environnement Python.
            goto :end
        )
    ) else (
        echo [ERREUR] Script introuvable: scripts\install_env.bat
        goto :end
    )
)
echo [OK] Environnement Python pret.
echo.

echo [4/5] Activation venv + preflight...
call ".\.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERREUR] Echec activation venv.
    goto :end
)

python scripts\preflight.py --quick
if errorlevel 1 (
    echo [ERREUR] Preflight KO. Verifiez .env, cles, et dependances.
    goto :end
)
echo [OK] Preflight valide.
echo.

echo [5/5] Lancement interface Streamlit...
python -m streamlit --version >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Streamlit indisponible dans .venv.
    echo          Relancez scripts\install_env.bat
    goto :end
)

echo.
echo [OK] Interface en cours de demarrage...
echo     URL locale: http://localhost:8501
echo     Ne fermez pas cette fenetre pendant l'utilisation.
echo.
python -m streamlit run app.py

:end
echo.
echo =======================================================
echo  Fin du script.
echo =======================================================
pause
exit /b
