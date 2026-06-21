@echo off
REM Start Backend API (Flask)
REM This script starts the Flask backend on http://localhost:5000

echo ========================================
echo Starting Voter List Backend API
echo ========================================
echo.
echo Backend will be available at: http://localhost:5000
echo.
echo To stop the server: Press Ctrl+C
echo.
pause

cd backend
python backend_api.py
