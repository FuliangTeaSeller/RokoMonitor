@echo off
cd /d "%~dp0.."
call conda activate rokomonitor
python tools/import_skills_from_html.py
call conda deactivate
pause
