@echo off
REM Change to project root (one level up from scripts/)
cd /d "%~dp0\.."

echo.
echo ========================================================
echo  Wildfire Prediction System - Quick Start Setup
echo ========================================================
echo.

echo Installing Python dependencies...
pip install pandas numpy scikit-learn matplotlib flask flask-cors joblib torch pillow scipy

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  Training RandomForest model (this may take 5-10 minutes)
echo ========================================================
echo.

set NO_PLOTS=1
python scripts/non-image-model.py

if errorlevel 1 (
    echo.
    echo ERROR: Model training failed
    pause
    exit /b 1
)

if not exist "wildfire_model.pkl" (
    echo.
    echo ERROR: Model file (wildfire_model.pkl) not found
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  SUCCESS! Setup complete - starting server
echo ========================================================
echo.
echo Open index.html in a browser while this server is running.
echo Press Ctrl+C to stop.
echo.

python server.py
pause
