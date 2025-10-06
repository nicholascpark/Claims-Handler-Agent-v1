@echo off
REM Unified startup script for Claims Handler Voice Agent (Backend + Frontend)

echo 🚀 Starting Claims Handler Voice Agent - Full Stack
echo ==================================================

REM Check if .env exists
if not exist ".env" (
    echo ❌ Error: .env file not found in project root
    echo 📝 Please copy .env.example to .env and configure your Azure credentials
    pause
    exit /b 1
)

REM Start backend
echo.
echo 📦 Starting Backend Server...
cd backend

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install dependencies
call venv\Scripts\activate.bat
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Start backend in new window
start "Backend Server" cmd /k "venv\Scripts\activate.bat && python main.py"
echo ✅ Backend starting on http://localhost:8000

cd ..

REM Wait for backend to be ready
echo ⏳ Waiting for backend to be ready...
timeout /t 3 /nobreak > nul

REM Start frontend
echo.
echo 📦 Starting Frontend Server...
cd frontend

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing npm dependencies...
    call npm install
)

REM Start frontend in new window
start "Frontend Server" cmd /k "npm run dev"
echo ✅ Frontend starting on http://localhost:5173

cd ..

echo.
echo ==================================================
echo ✅ Full Stack Running!
echo ==================================================
echo.
echo 🌐 Frontend: http://localhost:5173
echo 🔧 Backend:  http://localhost:8000
echo 📊 API Docs: http://localhost:8000/docs
echo.
echo Close the terminal windows to stop services
echo.
pause


