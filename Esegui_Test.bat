@echo off
rem Dove_Volo - esegue tutti i test automatici.
cd /d "%~dp0"
python -X utf8 -m unittest discover -s tests -t .
if errorlevel 1 echo. & echo ERRORE: qualche test non e' passato.
pause
