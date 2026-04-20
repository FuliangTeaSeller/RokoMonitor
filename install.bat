@echo off
chcp 65001 >nul
echo 正在安装依赖...

call conda activate rokomonitor
if errorlevel 1 (
    echo 错误: conda环境 rokomonitor 不存在
    echo 请先运行: conda create -n rokomonitor python=3.11
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo 依赖安装失败
    pause
    exit /b 1
)

echo 依赖安装完成
pause
