# Wildfire Prediction System - Complete Guide

## Overview

This is an **Educational Wildfire Simulator** that combines satellite imagery, fire drawing simulation, and machine learning prediction. Users can:

1. Select a U.S. state and satellite image
2. Draw a fire shape on the image
3. Input weather conditions for two timepoints (day of ignition and 3 days after)
4. Get a **predicted fire size** based on a trained RandomForest model

The system integrates:
- **Frontend**: HTML/CSS/JavaScript web interface
- **Backend**: Python Flask API
- **ML**: Scikit-learn RandomForest with 60+ engineered features

## Quick Start (Windows Users)

### Option 1: Automated Setup (Recommended)
```bash
start-setup.bat
```
This will:
- Install Python dependencies
- Train the RandomForest model
- Start the prediction server
- Guide you to open the website

### Option 1b: Verify Setup Works (Optional)
After setup completes, validate the system:
```bash
validate.bat
```
This checks:
- All files are present
- Python packages installed
- Model loads correctly
- ML pipeline works
- API server ready
- Frontend configured

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install pandas numpy scikit-learn matplotlib flask joblib

# 2. Train the model (takes 5-10 minutes)
python non-image-model.py

# 3. In a new terminal, start the server
python server.py

# 4. Open index.html in your web browser
```

### Starting the Server Later
After setup is complete, use:
```bash
start-server.bat
```

## Quick Start (Mac/Linux Users)

```bash
# 1. Install dependencies
pip install pandas numpy scikit-learn matplotlib flask joblib

# 2. Train the model
python3 non-image-model.py

# 3. Verify setup (optional)
python3 validate.py

# 4. In another terminal, start the server
python3 server.py

# 5. Open index.html in your web browser
```

## System Architecture

```
┌─────────────────────────────────────────┐
│         Browser (index.html)            │
│   - Select image                        │
│   - Draw fire shape                     │
│   - Enter weather conditions            │
│   - View predictions                    │
└──────────────┬──────────────────────────┘
               │ Weather data + image name
               ↓
┌─────────────────────────────────────────┐
│    Flask Server (server.py)             │
│    - Validates inputs                   │
│    - Looks up image coordinates         │
│    - Calls prediction model             │
└──────────────┬──────────────────────────┘
               │ Predicted acres
               ↓
┌─────────────────────────────────────────┐
│   ML Model (model.py)                   │
│   - Get terrain features from CSV       │
│   - Engineer 60+ features               │
│   - Predict using RandomForest          │
└──────────────┬──────────────────────────┘
               │
          Load CSV data &
        saved model file
```

## File Structure

### Core Application Files
- `index.html` - Main website
- `app.js` - Website logic (state management, drawing, weather input)
- `styles.css` - Styling with slide animations
- `about.html` - About page

### Python ML Pipeline
- `model.py` - Prediction module with feature engineering
- `server.py` - Flask API server
- `non-image-model.py` - Training script
- `prediction-client.js` - JavaScript API client

### Data Files
- `coordinates.csv` - Maps image names to latitude/longitude
- `mtbs_dataset(GoogleEarth+OpenMeteo).csv` - Historical fire data for training
- `wildfire_model.pkl` - Trained model (created during setup)

### Documentation
- `PREDICTION_SETUP.md` - Detailed setup instructions
- `ARCHITECTURE.md` - Technical architecture overview
- `SYSTEM_VALIDATION.md` - Verification checklist
- `README.md` - This file

### Utility Scripts
- `setup.py` - Python setup script (Unix/Mac/Linux)
- `start-setup.bat` - Windows setup launcher
- `start-server.bat` - Windows server starter

## How It Works

### User Workflow
1. **Select Image**: Choose a state, then click a satellite image to open the drawing interface
2. **Draw Fire**: Use the drawing tools to outline fire perimeter
3. **Enter Weather**: 
   - Day 0 (day of ignition): Temperature, humidity, precipitation, soil moisture, wind
   - Day 3 (3 days after ignition): Same parameters representing post-ignition conditions
4. **Get Prediction**: System predicts total acres burned based on location, terrain, and weather

### ML Workflow
1. **Terrain Lookup**: Image coordinates → Find terrain features (elevation, slope, vegetation)
2. **Feature Engineering**: User weather input + terrain → Generate 60+ predictive features
3. **Prediction**: RandomForest model predicts log-scale acres burned
4. **Result**: Convert log-scale back to acres and display to user

## Prediction Inputs

### User-Provided (from web form)
- **Day 0 (Ignition Day)**: Temperature, humidity, precipitation, soil moisture, wind speed, wind gust, wind direction
- **Day 3 (Post-Ignition)**: Same parameters representing conditions 3 days after fire ignition

### Automatically Looked Up
- **Image Coordinates**: From `coordinates.csv` based on selected image
- **Terrain Features**: From `mtbs_dataset.csv` using nearest-neighbor matching
  - Elevation, slope, aspect, NDVI, land cover classification

### Model-Generated Features (60+)
- Wind direction conversions (sine/cosine)
- Fire risk compounds (wind × dryness, etc.)
- Fuel moisture indices
- Post-ignition danger metrics
- Terrain-fire interactions

## Troubleshooting

### "Network error: Could not reach prediction server"
- Make sure `server.py` is running in another terminal
- Check that no other application is using port 5000
- Try refreshing the browser

### "Image not found in coordinates.csv"
- Verify the image name matches exactly (case-sensitive)
- Check that `coordinates.csv` contains the image

### "Model not found"
- Run `python non-image-model.py` to train and save the model
- Ensure `wildfire_model.pkl` exists in the same folder as `server.py`

### "ModuleNotFoundError: pandas"
- Install dependencies: `pip install pandas numpy scikit-learn flask joblib`
- Make sure you're using the same Python environment

### Slow predictions or server startup
- Model training takes 5-10 minutes (first-time only)
- First prediction request loads the model (may take 2-3 seconds)
- Subsequent predictions are <100ms

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Install dependencies | 2-5 min | One-time |
| Train model | 5-10 min | One-time |
| Server startup | 1-2 sec | Model loading |
| Single prediction | <100 ms | Per request |
| Model file size | 50-100 MB | wildfire_model.pkl |

## Technical Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: Python Flask, scikit-learn
- **Data Processing**: Pandas, NumPy
- **ML Model**: RandomForest (600 trees, max_depth=12)
- **Communication**: JSON over HTTP/REST

## Educational Value

This simulator demonstrates:
- **Machine Learning**: Training, feature engineering, prediction
- **Web APIs**: REST endpoints, async requests
- **Data Science**: Feature engineering, model evaluation
- **Full-Stack Development**: Frontend-backend integration
- **Real-World Problem**: Fire size prediction from weather data

## Next Steps

After verifying the system works:
1. **Explore the UI**: Try different images and weather conditions
2. **Analyze Results**: See how weather affects predictions
3. **Modify Features**: Edit `engineer_features()` in model.py to add new features
4. **Deploy**: Host on cloud platform (AWS, GCP, Heroku)
5. **Extend**: Add more features (historical fire data, seasonal patterns, etc.)

## Support & Documentation

- **Setup Issues**: See `PREDICTION_SETUP.md`
- **Architecture**: See `ARCHITECTURE.md`
- **Verification**: See `SYSTEM_VALIDATION.md`
- **Code Issues**: Check syntax errors with Python linter

## License

Educational purposes only. For research and learning use.

---

**System Status**: ✅ Ready for Use
**Last Updated**: 2026-04-28
