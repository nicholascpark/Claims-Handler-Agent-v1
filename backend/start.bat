@echo off
REM Start script for Claims Handler Voice Agent Backend

echo 🚀 Starting Claims Handler Voice Agent Backend...

REM Check if we're in the backend directory
if not exist "main.py" (
    echo ❌ Error: Please run this script from the backend directory
    echo    cd backend
    echo    start.bat
    pause
    exit /b 1
)

REM Check if .env exists in parent directory
if not exist "..\\.env" (
    echo ⚠️  Warning: .env file not found in project root
    if exist "..\\.env.example" (
        echo 📝 Copying .env.example to .env...
        copy ..\\.env.example ..\\.env
        echo 📝 Please edit .env with your Azure OpenAI credentials before continuing.
        pause
        exit /b 1
    ) else (
        echo ❌ Error: No .env.example found. Please create .env manually.
        pause
        exit /b 1
    )
)

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Verify activation
if "%VIRTUAL_ENV%"=="" (
    echo ❌ Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated: %VIRTUAL_ENV%

REM Install/upgrade dependencies
echo 📦 Installing dependencies...
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r ..\requirements.txt

REM Verify FastAPI is installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ❌ Error: FastAPI not installed correctly
    echo    Try: pip install -r ..\requirements.txt
    pause
    exit /b 1
)

REM Start server
echo.
echo ✅ Starting server on http://localhost:8000
echo    Press Ctrl+C to stop
echo.
python main.py

