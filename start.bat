@echo off
echo ========================================
echo 模块化LLM文献调研工具 v2.0
echo ========================================
echo.
echo 正在启动程序...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python环境
    echo 请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 启动主程序
python modular_research_gui.py

REM 如果程序异常退出，显示错误信息
if errorlevel 1 (
    echo.
    echo 程序异常退出，请检查错误信息
    echo 如需帮助，请查看README.md文档
    pause
)