@echo off
REM Voter List Search - Startup Script for Windows

echo.
echo ========================================
echo 🗳️  Voter List Search - Startup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js not found. Please install Node.js 14+
    pause
    exit /b 1
)

echo ✓ Python found
echo ✓ Node.js found
echo.

REM Check if dependencies are installed
if not exist "frontend\node_modules" (
    echo 📦 Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo ✓ Frontend dependencies installed
    echo.
)

REM Start Flask backend in new window
echo 🚀 Starting Flask API backend...
start "Voter List Backend API" python backend_api.py

REM Wait for backend to start
timeout /t 3 /nobreak

REM Start React frontend in new window
echo 🚀 Starting React frontend...
start "Voter List Frontend" cmd /k "cd frontend && npm run dev"

REM Open browser
timeout /t 5 /nobreak
echo 🌐 Opening application in browser...
start http://localhost:5173

echo.
echo ========================================
echo ✓ Application started!
echo ========================================
echo.
echo 📍 Frontend: http://localhost:5173
echo 📍 Backend API: http://localhost:5000
echo.
echo Press any key to close this window...
pause >nul
