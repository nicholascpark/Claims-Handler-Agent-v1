@echo off
REM Start script for FNOL Voice Agent Frontend (Windows)

echo [*] Starting FNOL Voice Agent Frontend...

REM Check if node_modules exists
if not exist "node_modules\" (
    echo [*] Installing dependencies...
    call npm install
)

REM Check if logo exists
if not exist "public\intactbot_logo.png" (
    echo [WARN] intactbot_logo.png not found in public directory
    echo Please copy the logo to frontend\public\intactbot_logo.png
)

REM Start development server
echo [OK] Starting development server on http://localhost:3000
call npm run dev
