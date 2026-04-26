@echo off
REM ============================================================
REM AFRACS one-time setup for Windows.
REM Run this ONCE on the demo PC (needs internet + MySQL/MariaDB).
REM After this finishes, use run.bat to launch the system.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo === AFRACS Setup ===
echo.

REM ---- 1. Locate Python 3.11 ----
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3.11"
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not on PATH.
        echo Install Python 3.11 from https://www.python.org/downloads/release/python-3110/
        echo Make sure to tick "Add Python to PATH" during install.
        pause
        exit /b 1
    )
    set "PY=python"
)

REM ---- 2. Create virtual environment ----
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists. Skipping.
)

call ".venv\Scripts\activate.bat"

REM ---- 3. Install dependencies ----
echo.
echo Installing Python packages (this may take a few minutes)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements. Check your internet connection.
    pause
    exit /b 1
)

REM ---- 4. Prepare .env ----
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy /Y ".env.example" ".env" >nul
        echo.
        echo [!] Edit .env to match your MySQL credentials before continuing.
        echo     Open .env in Notepad and set MYSQL_USER / MYSQL_PASSWORD.
        notepad .env
    )
)

REM ---- 5. Download face recognition models ----
echo.
echo Downloading face detection / recognition models...
python -m afracs.download_models
if errorlevel 1 (
    echo [WARN] Model download failed. Re-run setup once internet is available.
)

REM ---- 6. Initialize MySQL database ----
echo.
echo Initializing MySQL database (afracs)...
python -m afracs.db
if errorlevel 1 (
    echo [ERROR] Database init failed.
    echo - Make sure MariaDB/MySQL is installed and running.
    echo - Check MYSQL_USER and MYSQL_PASSWORD in .env.
    pause
    exit /b 1
)

echo.
echo === Setup complete ===
echo You can now double-click run.bat to launch AFRACS.
echo.
pause
endlocal
