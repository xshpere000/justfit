@echo off
REM 停止 JustFit 开发服务

echo 正在停止 JustFit 服务...

REM 停止 uvicorn 进程
taskkill /f /im uvicorn.exe >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JustFit Backend*" >nul 2>&1

REM 停止 node 进程（Vite dev server）
for /f "tokens=2" %%a in ('tasklist ^| findstr "node.exe"') do taskkill /f /pid %%a >nul 2>&1

echo 服务已停止。
pause
