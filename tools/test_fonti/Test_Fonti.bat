@echo off
rem Dove_Volo - test delle fonti. Scrive REPORT_FONTI.md in questa cartella.
rem Per riscaricare tutto: Test_Fonti.bat --aggiorna
cd /d "%~dp0"
python -I -X utf8 test_fonti.py %*
if errorlevel 1 echo. & echo ERRORE: il test non e' arrivato in fondo, guarda il messaggio qui sopra.
pause
