@echo off
chcp 65001 >nul 2>&1
title Reading App

echo.
echo ========================================
echo   My Study - Reading App
echo ========================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found!
    pause
    exit /b 1
)

echo [1/3] Installing Python packages...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
echo        Done.

echo.
echo [2/3] Installing Node packages...
cd /d "%~dp0frontend"
call npm install --silent
echo        Done.

echo.
echo [3/3] Starting servers...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do taskkill /f /pid %%a 2>nul

cd /d "%~dp0backend"
start "Backend-8000" cmd /c "title Backend:8000 && uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo        Waiting for backend...
timeout /t 3 /nobreak >nul

cd /d "%~dp0frontend"
start "Frontend-5173" cmd /c "title Frontend:5173 && npm run dev -- --host 0.0.0.0"

timeout /t 3 /nobreak >nul
start "" http://localhost:5173

echo.
echo ========================================
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo ========================================
echo.
echo Close this window to keep app running.
echo.
pause
