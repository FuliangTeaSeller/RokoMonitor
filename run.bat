@echo off
cd /d "%~dp0"
call conda activate rokomonitor
python -m src.main
call conda deactivate
