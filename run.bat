@echo off
chcp 65001 >nul
call conda activate rokomonitor
python -m src.main
