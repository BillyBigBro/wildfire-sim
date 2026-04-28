# End-to-End System Test Scenario

This document describes what will happen when a user deploys and uses the system.

## Test Prerequisites
- Windows 10/11 with Python 3.8+
- Internet connection (for dependency installation)
- ~500MB disk space
- ~10-15 minutes available

## Test Scenario Flow

### Phase 1: Setup (Windows User Path)

**Action:** User double-clicks `start-setup.bat`

**Expected Output:**
```
========================================================
 Wildfire Prediction System - Quick Start Setup
========================================================

📋 Installing Python dependencies
Running: pip install pandas numpy scikit-learn matplotlib flask joblib

✅ Installing Python dependencies - SUCCESS

📋 Training RandomForest model (this may take 5-10 minutes)
Running: python non-image-model.py

[Training output shown...]
✅ Model training - SUCCESS
✅ Model file saved: wildfire_model.pkl

========================================================
✅ SETUP COMPLETE!
========================================================

Next steps:
1. Start the prediction server in a new terminal:
   python server.py

2. Open index.html in a web browser
```

**Duration:** 15 minutes  
**Outcome:** wildfire_model.pkl created (50-100 MB)

---

### Phase 2: Validation (Optional)

**Action:** User double-clicks `validate.bat`

**Expected Output:**
```
========================================================
 Wildfire Prediction System - Post-Setup Validation
========================================================

STEP 1: Checking File Inventory
========================================================
  ✅ Web interface
  ✅ Frontend logic
  ✅ Styling
  ✅ API client
  ✅ ML prediction module
  ✅ Flask API server
  ✅ Training script
  ✅ Image coordinates
  ✅ Training data
  ✅ Trained model

STEP 2: Checking Python Packages
========================================================
  ✅ Pandas
  ✅ NumPy
  ✅ Scikit-learn
  ✅ Flask
  ✅ Joblib

STEP 3: Checking Trained Model
========================================================
  ✅ Model file exists
  ✅ Model loads successfully
  ✅ Model type: RandomForestRegressor

STEP 4: Testing ML Pipeline
========================================================
  ✅ ML pipeline works
  ✅ Sample prediction: 5234 acres

STEP 5: Testing API Server Startup
========================================================
  ✅ Flask app imports successfully
  ✅ /predict endpoint exists
  ✅ /health endpoint exists
  ✅ API server configuration valid

STEP 6: Checking Frontend Files
========================================================
  ✅ prediction-client.js included in HTML
  ✅ setCurrentImage function exists in app.js
  ✅ submitWeatherDataForPrediction function exists in app.js
  ✅ CSS transitions configured for animations

VALIDATION SUMMARY
========================================================
  ✅ PASS: File Inventory
  ✅ PASS: Python Packages
  ✅ PASS: Trained Model
  ✅ PASS: ML Pipeline
  ✅ PASS: API Server
  ✅ PASS: Frontend

✅ ALL VALIDATION CHECKS PASSED!
========================================================

Your system is ready to use!
```

**Duration:** 1-2 minutes  
**Outcome:** Confirmation that all systems operational

---

### Phase 3: Server Startup

**Action:** User opens new terminal and runs `python server.py`

**Expected Output:**
```
 * Serving Flask app 'server'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

**Status:** Server running and listening on localhost:5000  
**Outcome:** API ready to receive prediction requests

---

### Phase 4: Website Launch

**Action:** User opens `index.html` in web browser

**Expected Display:**
- Title: "Wildfire Prediction Simulator"
- Dropdown: State selection (with U.S. states)
- Images appear when state selected
- About page link
- Navigation buttons

**User Action:** Select state (e.g., "Arizona")

**Expected Outcome:**
- Images from Arizona appear below
- Each image is clickable
- Images labeled with fire event name/date

---

### Phase 5: Image Selection & Drawing

**User Action:** Click on a satellite image

**Expected Outcome:**
- Drawing interface opens
- Satellite image displayed
- Drawing tools appear (undo/done buttons)
- Drawing canvas ready for mouse input

**User Action:** Draw a fire perimeter on the image

**Expected Outcome:**
- Lines drawn as user clicks and drags
- Green polyline appears as fire outline
- Undo button works if clicked

**User Action:** Click "done" button

**Expected Outcome:**
- Drawing interface closes
- Weather input overlay appears
- Label shows: "Day 0 - Day of Ignition"
- Weather form displayed

---

### Phase 6: Day 0 Weather Input

**Weather Form Inputs Visible:**
- Temperature: Slider (-20 to 50°C)
- Humidity: Slider (0 to 100%)
- Precipitation: Slider (0 to 50mm)
- Soil Moisture: Slider (0 to 100%)
- Wind Speed: Slider (0 to 100 km/h)
- Wind Gust: Slider (0 to 150 km/h)
- Wind Direction: Compass/Angle selector

**Default Values Shown:**
- Temperature: 28°C
- Humidity: 35%
- Precipitation: 0mm
- Soil Moisture: 20%
- Wind Speed: 15 km/h
- Wind Gust: 35 km/h
- Wind Direction: 270° (West)

**User Action:** Adjust sliders to simulate hot, dry, windy conditions

**Expected Outcome:**
- Sliders move smoothly
- Values update in real-time
- Wind direction updates with angle/direction name

**User Action:** Click "done" button

**Expected Outcome:**
- Day 0 weather saved
- Overlay transitions smoothly (slides from left)
- New overlay appears from right
- Label shows: "Day 3 - Post-Ignition Conditions"

---

### Phase 7: Day 3 Weather Input

**Expected Outcome:**
- Same 7 weather parameters visible
- New form for day 3 conditions
- Smooth transition animation

**User Action:** Adjust sliders for day 3 (typically warmer, possibly different wind)

**Expected Outcome:**
- Sliders respond smoothly
- Values update

**User Action:** Click "done" button

**Expected Outcome:**
- Day 3 weather saved
- API request sent to server
- Overlay closes
- Alert box appears with result

---

### Phase 8: Prediction Results

**Expected Alert Message:**
```
Predicted Fire Size: 5234 acres

This prediction is based on:
- Location (terrain features)
- Weather conditions on day of ignition (Day 0)
- Weather conditions 3 days after ignition (Day 3)

The model uses a RandomForest trained on historical fire data.
```

**User Action:** Click OK

**Expected Outcome:**
- Alert closes
- Browser ready for another prediction
- Console shows full result (if developer opens console)

---

### Phase 9: Multiple Predictions

**User Action:** Try another image with different weather

**Expected Flow:**
1. Select different state
2. Click different satellite image
3. Draw another fire (or skip)
4. Fill day 0 weather
5. Fill day 3 weather
6. See prediction

**Expected Outcome:**
- System handles multiple predictions smoothly
- Previous results don't interfere
- Each prediction uses correct image and weather

---

## Error Scenario Tests

### Error Test 1: Network Error

**Setup:** Model.py deliberately fails

**User Action:** Click day 3 done

**Expected Outcome:**
```
Alert: "Error: Model prediction failed: No module named 'pandas'"
Console shows: {"error": "Model prediction failed: No module named 'pandas'"}
```

### Error Test 2: Image Not Found

**Setup:** coordinates.csv missing

**User Action:** Click day 3 done

**Expected Outcome:**
```
Alert: "Error: Image not found in coordinates.csv: 'badimage.tif'"
Console shows: {"error": "Image not found..."}
```

### Error Test 3: Server Not Running

**Setup:** Don't start server.py

**User Action:** Click day 3 done

**Expected Outcome:**
```
Alert: "Error: Could not reach prediction server. Make sure server.py is running."
Console shows network error
```

---

## Success Criteria

✅ **Phase 1 Success**
- Setup completes without errors
- Model file created (50-100 MB)
- Packages installed

✅ **Phase 2 Success**
- Validation script runs
- All checks pass
- ML pipeline makes test prediction

✅ **Phase 3 Success**
- Server starts on localhost:5000
- API endpoints available
- Health check responds

✅ **Phase 4 Success**
- Website loads in browser
- States display
- Images load

✅ **Phase 5 Success**
- Drawing interface works
- Fire outline can be drawn
- Undo function works

✅ **Phase 6 Success**
- Day 0 weather form displays
- All 7 sliders work
- Values can be adjusted
- Transition to day 3 smooth

✅ **Phase 7 Success**
- Day 3 weather form displays
- Sliders work
- Submit button triggered

✅ **Phase 8 Success**
- API returns prediction
- Alert shows acres burned
- Result is number > 0

✅ **Phase 9 Success**
- Multiple predictions work
- System state managed correctly
- No memory leaks

---

## Performance Benchmarks

| Operation | Target | Acceptable |
|-----------|--------|-----------|
| Setup time | 15 min | <20 min |
| Model training | 5-10 min | <15 min |
| Validation | 2 min | <3 min |
| Server startup | 2 sec | <5 sec |
| Website load | <1 sec | <3 sec |
| Image load | <500ms | <2 sec |
| Prediction API | <500ms | <2 sec |
| Slider response | Real-time | <100ms |
| Overlay transition | 420ms | 300-500ms |

---

## Browser Compatibility Matrix

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Latest | ✅ Should work |
| Firefox | Latest | ✅ Should work |
| Safari | Latest | ✅ Should work |
| Edge | Latest | ✅ Should work |
| IE 11 | Latest | ⚠️ May not work (no ES6 support) |

---

## System Assumptions

1. **Python 3.8+** installed and in PATH
2. **pip** available for package installation
3. **500MB+ disk space** for model and data
4. **localhost:5000** not already in use
5. **JavaScript enabled** in browser
6. **Modern browser** with ES6 support
7. **File permissions** allow reading/writing

---

## Sign-Off

When all phases complete successfully:
- ✅ System is working as designed
- ✅ All features operational
- ✅ All integrations functional
- ✅ Ready for production use
- ✅ Ready for educational deployment

---

**Test Date:** [User runs this]  
**Test Status:** [Pass/Fail]  
**Notes:** [User documents any issues]  

---

**End of Test Scenario**

When a user completes this entire scenario successfully, the system is proven to work correctly and is ready for use.
