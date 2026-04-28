@echo off
REM Wildfire Prediction System - Validation Script (Windows)

echo.
echo ========================================================
echo  Wildfire Prediction System - Post-Setup Validation
echo ========================================================
echo.

python validate.py

if errorlevel 1 (
    echo.
    echo Validation failed. Check the output above for issues.
    pause
    exit /b 1
) else (
    echo.
    echo Validation passed! System is ready to use.
    pause
    exit /b 0
)
