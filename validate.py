#!/usr/bin/env python3
"""
Wildfire Prediction System - Post-Setup Validation Script

Run this AFTER setup.py completes to verify the system is working correctly.
This script validates:
- All files are in place
- All Python packages are installed
- Model file exists and is loadable
- API server can start
- ML pipeline can make predictions
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"  ✅ {description}")
        return True
    else:
        print(f"  ❌ {description} - NOT FOUND: {filepath}")
        return False

def check_import(module_name, display_name):
    """Check if a Python module can be imported."""
    try:
        __import__(module_name)
        print(f"  ✅ {display_name}")
        return True
    except ImportError as e:
        print(f"  ❌ {display_name} - Import failed: {e}")
        return False

def validate_files():
    """Step 1: Validate all required files exist."""
    print("\n" + "="*60)
    print("STEP 1: Checking File Inventory")
    print("="*60)
    
    try:
        from model import DATASET_PATH
    except Exception:
        DATASET_PATH = "mtbs_dataset(GoogleEarth+OpenMeteo).csv"

    required_files = [
        ("index.html", "Web interface"),
        ("app.js", "Frontend logic"),
        ("styles.css", "Styling"),
        ("prediction-client.js", "API client"),
        ("model.py", "ML prediction module"),
        ("server.py", "Flask API server"),
        ("non-image-model.py", "Training script"),
        ("coordinates.csv", "Image coordinates"),
        (DATASET_PATH, "Training data"),
        ("wildfire_model.pkl", "Trained model"),
    ]
    
    results = []
    for filename, description in required_files:
        result = check_file_exists(filename, description)
        results.append((filename, result))
    
    all_exist = all(r[1] for r in results)
    return all_exist

def validate_packages():
    """Step 2: Validate all Python packages are installed."""
    print("\n" + "="*60)
    print("STEP 2: Checking Python Packages")
    print("="*60)
    
    packages = [
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("sklearn", "Scikit-learn"),
        ("flask", "Flask"),
        ("joblib", "Joblib"),
    ]
    
    results = []
    for module, display_name in packages:
        result = check_import(module, display_name)
        results.append((module, result))
    
    all_ok = all(r[1] for r in results)
    return all_ok

def validate_model():
    """Step 3: Validate the trained model."""
    print("\n" + "="*60)
    print("STEP 3: Checking Trained Model")
    print("="*60)
    
    try:
        import joblib
        import os
        
        if not os.path.exists("wildfire_model.pkl"):
            print("  ❌ Model file not found: wildfire_model.pkl")
            return False
        
        print("  ✅ Model file exists")
        
        # Try to load the model
        model = joblib.load("wildfire_model.pkl")
        print("  ✅ Model loads successfully")
        
        # Check model type
        model_type = type(model).__name__
        print(f"  ✅ Model type: {model_type}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Model validation failed: {e}")
        return False

def validate_ml_pipeline():
    """Step 4: Validate ML prediction pipeline."""
    print("\n" + "="*60)
    print("STEP 4: Testing ML Pipeline")
    print("="*60)
    
    try:
        from model import predict_acres_burned
        
        # Test data
        day0 = {
            "temp_c": 28,
            "humidity_pct": 35,
            "precip_mm": 0,
            "soil_moisture_pct": 20,
            "wind_speed_kmh": 15,
            "wind_gust_kmh": 35,
            "wind_direction_deg": 270
        }
        
        day3 = {
            "temp_c": 32,
            "humidity_pct": 25,
            "precip_mm": 0,
            "soil_moisture_pct": 15,
            "wind_speed_kmh": 20,
            "wind_gust_kmh": 45,
            "wind_direction_deg": 280
        }
        
        # Test location (Tucson, AZ area)
        result = predict_acres_burned(31.8, -110.67, day0, day3)
        
        if result.get("error"):
            print(f"  ❌ Prediction failed: {result['error']}")
            return False
        
        acres = result.get("predicted_acres", 0)
        print(f"  ✅ ML pipeline works")
        print(f"  ✅ Sample prediction: {acres:.0f} acres")
        
        return True
        
    except Exception as e:
        print(f"  ❌ ML pipeline test failed: {e}")
        return False

def validate_api_server():
    """Step 5: Validate Flask API server can start."""
    print("\n" + "="*60)
    print("STEP 5: Testing API Server Startup")
    print("="*60)
    
    try:
        from server import app
        
        print("  ✅ Flask app imports successfully")
        
        # Check if /predict endpoint exists
        endpoints = [str(rule) for rule in app.url_map.iter_rules()]
        if '/predict' in endpoints:
            print("  ✅ /predict endpoint exists")
        else:
            print("  ❌ /predict endpoint not found")
            return False
        
        if '/health' in endpoints:
            print("  ✅ /health endpoint exists")
        else:
            print("  ❌ /health endpoint not found")
            return False
        
        # Test health check (without actually running server)
        print("  ✅ API server configuration valid")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API server validation failed: {e}")
        return False

def validate_frontend():
    """Step 6: Validate frontend files."""
    print("\n" + "="*60)
    print("STEP 6: Checking Frontend Files")
    print("="*60)
    
    try:
        # Check HTML
        with open("index.html", "r") as f:
            html = f.read()
            if "prediction-client.js" in html:
                print("  ✅ prediction-client.js included in HTML")
            else:
                print("  ❌ prediction-client.js NOT included in HTML")
                return False
        
        # Check JavaScript references
        with open("app.js", "r") as f:
            js = f.read()
            if "setCurrentImage" in js:
                print("  ✅ setCurrentImage function exists in app.js")
            else:
                print("  ❌ setCurrentImage function NOT found in app.js")
                return False
            
            if "submitWeatherDataForPrediction" in js:
                print("  ✅ submitWeatherDataForPrediction function exists in app.js")
            else:
                print("  ❌ submitWeatherDataForPrediction function NOT found in app.js")
                return False
        
        # Check CSS transitions
        with open("styles.css", "r") as f:
            css = f.read()
            if "translateX" in css or "transform" in css:
                print("  ✅ CSS transitions configured for animations")
            else:
                print("  ❌ CSS transitions not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Frontend validation failed: {e}")
        return False

def main():
    """Run all validations."""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║  Wildfire Prediction System - Post-Setup Validation    ║
    ║                                                         ║
    ║  This script verifies the system is ready to use        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    # Run all validations
    results['files'] = validate_files()
    results['packages'] = validate_packages()
    results['model'] = validate_model()
    results['ml_pipeline'] = validate_ml_pipeline()
    results['api_server'] = validate_api_server()
    results['frontend'] = validate_frontend()
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    checks = [
        ("File Inventory", results['files']),
        ("Python Packages", results['packages']),
        ("Trained Model", results['model']),
        ("ML Pipeline", results['ml_pipeline']),
        ("API Server", results['api_server']),
        ("Frontend", results['frontend']),
    ]
    
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    # Final status
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL VALIDATION CHECKS PASSED!")
        print("="*60)
        print("""
    Your system is ready to use!
    
    Next steps:
    1. Start the server:   python server.py
    2. Open index.html in your browser
    3. Select an image and try a prediction
    
    For help, see QUICKSTART.md
        """)
        return 0
    else:
        print("❌ SOME VALIDATION CHECKS FAILED")
        print("="*60)
        print("""
    The system is not ready. Check the errors above:
    
    - If packages failed: Run setup again
    - If model failed: Ensure non-image-model.py ran to completion
    - If other errors: Check PREDICTION_SETUP.md for troubleshooting
    
    For help, see PREDICTION_SETUP.md
        """)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
