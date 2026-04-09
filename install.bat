@echo off
echo ========================================
echo 模块化LLM文献调研工具 v2.0 - 安装脚本
echo ========================================
echo.

REM 检查Python是否安装
echo 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python环境
    echo 请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python环境检查通过
python --version
echo.

REM 升级pip
echo 升级pip...
python -m pip install --upgrade pip
echo.

REM 安装依赖包
echo 安装依赖包...
python -m pip install -r requirements.txt
echo.

REM 检查关键依赖
echo 检查关键依赖安装情况...
python -c "import tkinter; print('✓ tkinter 可用')" 2>nul || echo "✗ tkinter 不可用"
python -c "import requests; print('✓ requests 已安装')" 2>nul || echo "✗ requests 安装失败"
python -c "import pywinauto; print('✓ pywinauto 已安装')" 2>nul || echo "✗ pywinauto 安装失败"
python -c "import psutil; print('✓ psutil 已安装')" 2>nul || echo "✗ psutil 安装失败"
python -c "import openai; print('✓ openai 已安装')" 2>nul || echo "✗ openai 安装失败"
python -c "import fitz; print('✓ PyMuPDF 已安装')" 2>nul || echo "✗ PyMuPDF 安装失败"
echo.

echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 使用说明:
echo 1. 双击 start.bat 启动程序
echo 2. 或在命令行运行: python modular_research_gui.py
echo 3. 推荐先配置环境变量 DEEPSEEK_API_KEY
echo 4. 详细使用说明请查看 README.md
echo.
echo 注意事项:
echo - 需要DeepSeek API密钥才能使用LLM功能
echo - PDF下载功能需要安装Microsoft Edge和Zotero
echo - 建议在稳定网络环境下使用
echo.
pause
