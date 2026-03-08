@echo off
REM JustFit 开发模式启动脚本 (Windows)

echo.
echo ============================================
echo  JustFit 开发模式启动
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.14+
    pause
    exit /b 1
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

REM 创建日志目录
if not exist logs mkdir logs

echo [1/2] 启动后端 (FastAPI) ...
start "JustFit Backend" cmd /c "cd backend && python -m uvicorn app.main:app --reload --port 22631"

echo [2/2] 启动前端 (Vite) ...
timeout /t 2 /nobreak >nul
start "JustFit Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo ============================================
echo  服务已启动！
echo ============================================
echo  后端 API: http://localhost:22631
echo  API 文档: http://localhost:22631/docs
echo  前端界面: http://localhost:22632
echo.
echo  按任意键关闭此窗口（服务将继续运行）
pause >nul
