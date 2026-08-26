@echo off
echo ============================================================
echo Bylix Email - Backend Server Startup
echo ============================================================
echo.

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting backend server...
echo Server will be available at http://127.0.0.1:8000
echo Press Ctrl+C to stop the server
echo.

python run.py

pause
