# Guide Utilisation - The Sovereign (AEBM V5)

## 1. Public cible
Ce guide est pour des utilisateurs non techniques.
Objectif: lancer l'application localement et utiliser les modes Interne/Candidat sans configuration complexe.

## 2. Prerequis (une seule fois)
1. Windows
2. Python 3.12 installe (cocher "Add Python to PATH" pendant l'installation)
3. Projet decompresse dans un dossier local

Note:
- Docker n'est pas requis en mode Cloud.
- Le fichier `.env` n'est pas fourni dans le zip (normal, pour la securite des cles).

## 3. Configuration .env (mode Cloud recommande)
Si `.env` est absent, `Demarrer_The_Sovereign.bat` le cree automatiquement et ouvre Notepad.

Vous devez remplir:
- `AEBM_NEO4J_MODE=cloud`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `GROQ_API_KEY`

Exemple:
```env
AEBM_NEO4J_MODE=cloud
NEO4J_URI=neo4j+s://YOUR_AURA_INSTANCE_ID.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=YOUR_AURA_PASSWORD
GROQ_API_KEY=YOUR_GROQ_API_KEY
LLM_MODEL=llama-3.3-70b-versatile
```

Important:
- Le fichier doit s'appeler exactement `.env` (pas `.env.txt`).
- En mode Cloud, Docker n'est pas utilise.

## 4. Installation automatique (une seule fois)
Dans PowerShell, depuis la racine du projet:
```powershell
.\scripts\install_env.bat
```

Ce script:
1. cree/active `.venv`
2. installe les dependances
3. lance un preflight

## 5. Lancement quotidien (one-click)
Double-cliquer:
- `Demarrer_The_Sovereign.bat`

Le script fait automatiquement:
1. verification du mode Neo4j (Cloud ou local)
2. verification/enrichissement de `.env`
3. verification environnement Python
4. preflight
5. lancement Streamlit

Puis ouvrir:
- http://localhost:8501

Important:
- Ne pas fermer la fenetre noire pendant l'utilisation.

## 6. Utilisation fonctionnelle
### 6.1 Mode Interne
1. Uploader l'offre PDF
2. Lancer la recherche vectorielle
3. Lancer l'audit d'un profil shortlist
4. Lire le rapport dans les onglets resultats

### 6.2 Mode Candidat (CV seul)
1. Uploader uniquement le CV PDF
2. (Optionnel) secteurs/domaines cibles
3. Lancer "Generer mon diagnostic CV"
4. Lire diagnostic CV + postes suggeres

## 7. Mise a jour base candidats
### Option A (interface)
Dans Mode Interne > expander "Maintenance donnees (Admin)":
- "Lancer Ingestion + Reindexation"

### Option B (terminal)
```powershell
.\.venv\Scripts\python.exe run_phase1_ingestion.py
.\.venv\Scripts\python.exe reindex.py
```

## 8. Depannage rapide
### Cas 1 - Module manquant / import error
```powershell
.\scripts\install_env.bat
```

### Cas 2 - Preflight KO
```powershell
.\.venv\Scripts\python.exe .\scripts\preflight.py --quick
```
Corriger les lignes `[FAIL]`.

### Cas 3 - Erreur Neo4j en mode Cloud
Verifier dans `.env`:
- `AEBM_NEO4J_MODE=cloud`
- `NEO4J_URI=neo4j+s://...`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

Tester la connectivite:
```powershell
.\.venv\Scripts\python.exe -c "from dotenv import dotenv_values; c=dotenv_values('.env'); from neo4j import GraphDatabase; d=GraphDatabase.driver(c['NEO4J_URI'], auth=(c['NEO4J_USER'], c['NEO4J_PASSWORD'])); d.verify_connectivity(); print('AURA_AUTH_OK'); d.close()"
```

### Cas 4 - Page Streamlit vide / erreur JS
1. Ouvrir en navigation privee
2. Faire `Ctrl+F5`
3. Relancer `Demarrer_The_Sovereign.bat`

## 9. Arret propre
1. Fermer l'onglet navigateur
2. Fermer la fenetre noire du script

## 10. Commandes qualite (equipe technique)
Tests D1:
```powershell
.\scripts\test_d1.bat
```

Tests D1 + couverture:
```powershell
.\scripts\test_d1.bat cov 20
```

Pack soutenance:
```powershell
.\scripts\test_e1_pack.ps1
.\scripts\test_e2_checklist.ps1
.\scripts\test_e3_dryrun.ps1
.\scripts\test_e4_qa.ps1
.\scripts\test_e5_bundle.ps1
.\scripts\test_e6_release.ps1
```
