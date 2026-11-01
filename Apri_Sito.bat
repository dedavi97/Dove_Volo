@echo off
rem Dove_Volo - apre il sito nel browser, da questo PC.
cd /d "%~dp0"
python -X utf8 tools\sito_locale.py
if errorlevel 1 pause
