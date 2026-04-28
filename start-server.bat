@echo off
REM Wildfire Prediction System - Start Server Only
REM Run this after setup.py has completed

echo.
echo ========================================================
echo  Wildfire Prediction System - Server
echo ========================================================
echo.

if not exist "wildfire_model.pkl" (
    echo ERROR: Model file not found (wildfire_model.pkl)
    echo.
    echo Please run setup.py first to train the model
    pause
    exit /b 1
)

echo Starting prediction server on http://localhost:5000
echo.
echo Open your index.html file in a web browser
echo while this server is running.
echo.
echo Press Ctrl+C to stop the server.
echo.

python server.py

pause
