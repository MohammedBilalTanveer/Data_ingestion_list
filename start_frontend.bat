@echo off
REM Start Frontend (React with Vite)
REM This script starts the development server on http://localhost:5173

echo ========================================
echo Starting Voter List Frontend
echo ========================================
echo.
echo Frontend will be available at: http://localhost:5173
echo Backend should be running on: http://localhost:5000
echo.
echo To stop the server: Press Ctrl+C
echo.
pause

cd voter_official\frontend
npm run dev
