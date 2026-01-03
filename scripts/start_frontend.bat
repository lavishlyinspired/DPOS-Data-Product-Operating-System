@echo off
REM DPOS Frontend Startup Script (Windows)
REM Starts the React/Vite development server

echo ==================================================
echo DPOS - Data Product Operating System
echo Starting Frontend Development Server...
echo ==================================================

cd /d "%~dp0..\frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo.
    echo Installing dependencies...
    call npm install
)

echo.
echo ==================================================
echo Starting Vite dev server on http://localhost:3000
echo API requests will be proxied to http://localhost:8000
echo ==================================================
echo.

npm run dev
