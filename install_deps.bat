@echo off
echo === 安装项目依赖 ===
cd /d "%~dp0"
call conda activate rokomonitor
pip install -r requirements.txt
call conda deactivate
echo === 依赖安装完成 ===
pause
