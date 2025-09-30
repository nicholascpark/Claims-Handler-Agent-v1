@echo off
REM Master start script for FNOL Voice Agent (Windows)
REM Starts both backend and frontend in separate command windows

echo [*] FNOL Voice Agent - Starting All Services
echo ============================================

REM Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found in project root
    echo Please create .env file with Azure OpenAI credentials
    echo See SETUP_GUIDE.md for details
    exit /b 1
)

echo [OK] Environment file found

REM Start backend in new window
echo Starting Backend...
start "FNOL Backend" cmd /k "cd backend && start.bat"

REM Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

REM Start frontend in new window
echo Starting Frontend...
start "FNOL Frontend" cmd /k "cd frontend && start.bat"

echo.
echo [OK] Services starting...
echo.
echo [*] Backend:  http://localhost:8000
echo [*] Frontend: http://localhost:3000
echo.
echo [WAIT] Wait for both services to initialize, then open http://localhost:3000
echo.
echo To stop services:
echo   - Close the command windows
echo   - Or press Ctrl+C in each window
echo.
