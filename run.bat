@echo off
REM ============================================================
REM AFRACS launcher for Windows.
REM Double-click to start the Admin Dashboard + Cabinet UI.
REM Run setup.bat first if you haven't already.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

REM Mock GPIO so it runs on Windows without real Raspberry Pi hardware.
set "GPIOZERO_PIN_FACTORY=mock"

REM ---- Launch admin dashboard in a separate window ----
start "AFRACS Dashboard" cmd /k "call .venv\Scripts\activate.bat && set GPIOZERO_PIN_FACTORY=mock && echo Dashboard running at http://127.0.0.1:5000 && python dashboard.py"

REM Give Flask a couple of seconds to boot before opening the browser.
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"

REM ---- Launch cabinet UI in this window ----
echo.
echo Starting Cabinet UI... (close this window to stop)
echo.
call ".venv\Scripts\activate.bat"
python cabinet.py

endlocal
