@echo off
rem Dove_Volo - riscarica i confini dei paesi per lo sfondo della mappa. Serve di rado.
cd /d "%~dp0.."
python -X utf8 tools\prepara_mappa.py
pause
