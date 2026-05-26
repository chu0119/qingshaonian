@echo off
chcp 65001 >nul
echo ============================================
echo   青少年风险防范测评管理系统 - 一键启动
echo ============================================
echo.

:: 清理旧进程
echo [1/4] 正在清理旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo       旧进程已清理

:: 清理缓存
echo [2/4] 正在清理缓存...
if exist "frontend\node_modules\.vite" rmdir /s /q "frontend\node_modules\.vite" >nul 2>&1
echo       缓存已清理

:: 启动后端
echo [3/4] 正在启动后端服务 (端口 8000)...
start "青少年测评-后端" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: 等待后端启动
timeout /t 8 /nobreak >nul

:: 启动前端
echo [4/4] 正在启动前端服务 (端口 3000)...
start "青少年测评-前端" cmd /c "cd /d %~dp0frontend && npx vite --host 0.0.0.0 --port 3000"

echo.
echo ============================================
echo   启动完成！
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000/docs
echo   默认账号: admin / admin123
echo ============================================
echo.
echo 按任意键退出...
pause >nul
