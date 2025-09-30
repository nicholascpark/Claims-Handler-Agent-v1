@echo off
REM Start script for FNOL Voice Agent Backend (Windows)

echo [*] Starting FNOL Voice Agent Backend...

REM Check if virtual environment exists
if not exist "venv\" (
    echo [*] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [*] Installing dependencies...
pip install -q -r requirements.txt

REM Check for .env file
if not exist "../.env" (
    echo [WARN] .env file not found in project root
    echo Please create .env file with your Azure OpenAI credentials
    echo You can copy .env.example as a template
    pause
)

REM Start server
echo [OK] Starting server on http://localhost:8000
python server.py
