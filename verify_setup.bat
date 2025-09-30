@echo off
REM Verification script for FNOL Voice Agent setup (Windows)

echo [*] FNOL Voice Agent - Setup Verification
echo ==========================================
echo.

set ISSUES=0

REM Check prerequisites
echo [*] Checking Prerequisites...
echo -----------------------------

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] python found
    python --version
) else (
    echo [ERROR] python not found
    set /a ISSUES+=1
)

where node >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] node found
    node --version
) else (
    echo [ERROR] node not found
    set /a ISSUES+=1
)

where npm >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] npm found
    npm --version
) else (
    echo [ERROR] npm not found
    set /a ISSUES+=1
)
echo.

REM Check backend
echo [*] Checking Backend Structure...
echo -----------------------------
if exist "backend\" (echo [OK] backend\) else (echo [ERROR] backend\ & set /a ISSUES+=1)
if exist "backend\server.py" (echo [OK] backend\server.py) else (echo [ERROR] backend\server.py & set /a ISSUES+=1)
if exist "backend\requirements.txt" (echo [OK] backend\requirements.txt) else (echo [ERROR] backend\requirements.txt & set /a ISSUES+=1)
if exist "backend\Dockerfile" (echo [OK] backend\Dockerfile) else (echo [ERROR] backend\Dockerfile & set /a ISSUES+=1)
echo.

REM Check frontend
echo [*] Checking Frontend Structure...
echo -----------------------------
if exist "frontend\" (echo [OK] frontend\) else (echo [ERROR] frontend\ & set /a ISSUES+=1)
if exist "frontend\src\" (echo [OK] frontend\src\) else (echo [ERROR] frontend\src\ & set /a ISSUES+=1)
if exist "frontend\package.json" (echo [OK] frontend\package.json) else (echo [ERROR] frontend\package.json & set /a ISSUES+=1)
if exist "frontend\public\intactbot_logo.png" (echo [OK] frontend\public\intactbot_logo.png) else (echo [ERROR] frontend\public\intactbot_logo.png & set /a ISSUES+=1)
echo.

REM Check voice_langgraph
echo [*] Checking voice_langgraph...
echo -----------------------------
if exist "voice_langgraph\" (echo [OK] voice_langgraph\) else (echo [ERROR] voice_langgraph\ & set /a ISSUES+=1)
if exist "voice_langgraph\voice_agent.py" (echo [OK] voice_langgraph\voice_agent.py) else (echo [ERROR] voice_langgraph\voice_agent.py & set /a ISSUES+=1)
echo.

REM Check configuration
echo [*] Checking Configuration...
echo -----------------------------
if exist ".env" (
    echo [OK] .env file exists
) else (
    echo [WARN] .env file not found ^(copy from .env.example^)
    set /a ISSUES+=1
)

if exist ".env.example" (
    echo [OK] .env.example template available
) else (
    echo [WARN] .env.example not found
)
echo.

REM Check documentation
echo [*] Checking Documentation...
echo -----------------------------
if exist "QUICKSTART.md" (echo [OK] QUICKSTART.md) else (echo [ERROR] QUICKSTART.md & set /a ISSUES+=1)
if exist "SETUP_GUIDE.md" (echo [OK] SETUP_GUIDE.md) else (echo [ERROR] SETUP_GUIDE.md & set /a ISSUES+=1)
echo.

REM Summary
echo [*] Summary
echo ==========================================
if %ISSUES% equ 0 (
    echo [SUCCESS] All checks passed! Setup looks good.
    echo.
    echo Next steps:
    echo   1. Configure .env if not already done
    echo   2. Run: start_all.bat
    echo   3. Open: http://localhost:3000
    echo   4. Click 'Call Agent' and start talking!
) else (
    echo [FAILED] Found %ISSUES% issue^(s^)
    echo.
    echo Please resolve the issues above before starting.
    echo See SETUP_GUIDE.md for detailed instructions.
)

pause
