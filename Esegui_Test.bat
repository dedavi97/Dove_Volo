@echo off
rem Dove_Volo - esegue tutti i test automatici: scanner (Python) e sito (Node, se c'e').
cd /d "%~dp0"
set ERRORI=0
python -X utf8 -m unittest discover -s tests -t .
if errorlevel 1 set ERRORI=1
where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo Node non e' installato: i test del sito sono stati saltati.
) else (
  node --test "tests/*.test.mjs"
  if errorlevel 1 set ERRORI=1
)
if %ERRORI%==1 echo. & echo ERRORE: qualche test non e' passato.
pause
