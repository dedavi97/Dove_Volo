@echo off
rem Dove_Volo - scarica i dati, mostra le differenze e chiede se pubblicarli.
cd /d "%~dp0"
python -X utf8 -m scanner %*
if errorlevel 1 echo. & echo ERRORE: l'aggiornamento non e' arrivato in fondo, guarda il messaggio qui sopra.
pause
