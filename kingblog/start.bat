@echo off
REM 解决编译和运行时中文乱码问题（切换到 UTF-8）
chcp 65001 >nul
set LANG=zh_CN.UTF-8
set LC_ALL=zh_CN.UTF-8

cd /d %~dp0
echo [1/2] 构建生产版本...
call npm run build
if %ERRORLEVEL% NEQ 0 (
  echo 构建失败，按任意键退出
  pause
  exit /b 1
)
echo [2/2] 启动服务...
call npm start

