@echo off
REM Wildfire Prediction System - Quick Start (Windows)
REM This batch file runs the setup and then starts the server

echo.
echo ========================================================
echo  Wildfire Prediction System - Quick Start Setup
echo ========================================================
echo.

REM Step 1: Install dependencies
echo Installing Python dependencies...
pip install pandas numpy scikit-learn matplotlib flask flask-cors joblib

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Step 2: Train the model
echo.
echo ========================================================
echo  Training RandomForest model (this may take 5-10 minutes)
echo ========================================================
echo.

set NO_PLOTS=1
python non-image-model.py

if errorlevel 1 (
    echo.
    echo ERROR: Model training failed
    pause
    exit /b 1
)

REM Step 3: Check if model was created
if not exist "wildfire_model.pkl" (
    echo.
    echo ERROR: Model file (wildfire_model.pkl) not found
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  SUCCESS! Setup complete
echo ========================================================
echo.
echo The prediction server will now start...
echo.
echo Open a web browser and navigate to your index.html file
echo while this server is running.
echo.
echo Press Ctrl+C to stop the server.
echo.

REM Step 4: Start the server
python server.py

pause
