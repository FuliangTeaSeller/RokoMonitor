@echo off
cd /d "%~dp0.."

echo ========================================
echo 第一步：激活conda环境并安装依赖
echo ========================================
call conda activate rokomonitor
pip install -r requirements.txt

echo.
echo ========================================
echo 第二步：测试依赖是否安装成功
echo ========================================
python tools/test_dependencies.py

if errorlevel 1 (
    echo.
    echo 依赖安装失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo 第三步：运行技能导入脚本
echo ========================================
python tools/import_skills_from_html.py

echo.
echo ========================================
echo 完成！
echo ========================================
call conda deactivate
pause
