@echo off
REM DPOS Full Stack Startup Script (Windows)
REM Starts both backend and frontend servers

echo ==================================================
echo DPOS - Data Product Operating System
echo Starting Full Stack Application...
echo ==================================================
echo.

REM Start backend in a new window
echo Starting Backend Server...
start "DPOS Backend" cmd /k "cd /d %~dp0.. && python scripts\start_backend.py"

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak > nul

REM Start frontend in a new window
echo Starting Frontend Server...
start "DPOS Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ==================================================
echo Both servers are starting:
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ==================================================
echo.
echo Press any key to exit this window...
pause > nul
