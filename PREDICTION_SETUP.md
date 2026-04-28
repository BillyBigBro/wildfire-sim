# Wildfire Prediction Model Setup & Usage

This guide explains how to train the model, run the prediction server, and integrate predictions into the website.

## File Structure

- **model.py** — Core prediction module with feature engineering and inference functions
- **non-image-model.py** — Training script (trains the RandomForest model)
- **server.py** — Flask API server for predictions
- **prediction-client.js** — JavaScript client that calls the API
- **app.js** — Main website logic (updated to call setCurrentImage and submit predictions)
- **index.html** — Updated to include prediction-client.js

## Setup Steps

### 1. Install Python Dependencies

```bash
pip install pandas numpy scikit-learn matplotlib flask joblib
```

### 2. Prepare Data Files

Before training, ensure you have:

- **mtbs_dataset(GoogleEarth+OpenMeteo).csv** — Full dataset with terrain features + weather for all historical fires
  - Columns: lat, lon, elevation_m, slope_deg, aspect_sin, aspect_cos, ndvi, land_cover, acres_burned, and 60+ weather features
  - Place in the wildfire-sim folder

- **coordinates.csv** — Already in the project; links image names to lat/lon

### 3. Train the Model

```bash
python non-image-model.py
```

This will:
1. Load the MTBS dataset
2. Apply feature engineering
3. Train a RandomForest model with 600 trees
4. Display performance metrics
5. Show 20 example predictions
6. **Save the model to `wildfire_model.pkl`**

⏱️ This may take 5-10 minutes depending on dataset size.

### 4. Run the Prediction Server

In a separate terminal:

```bash
python server.py
```

Output should show:
```
Starting Wildfire Prediction API server...
Server running on http://localhost:5000
Health check: http://localhost:5000/health
Prediction endpoint: POST http://localhost:5000/predict
```

### 5. Use the Website

1. Open `index.html` in a browser
2. Select a state
3. Click an image to open the drawing interface
4. Draw a fire shape
5. Fill in weather for day of ignition → Click "done"
6. Fill in weather for day 3 → Click "done"
7. **Automatic prediction will be sent to the API**
8. Result alert shows: **"Predicted Fire Size: X acres"**

## How It Works

### Data Flow

```
User Input (Browser)
    ↓
prediction-client.js (formatWeatherForAPI)
    ↓
server.py (Flask API)
    ↓
model.py (build_prediction_input → engineer_features → predict_acres_burned)
    ↓
mtbs_dataset.csv lookup (terrain data for image location)
    ↓
RandomForest model
    ↓
Prediction result (acres)
    ↓
Display to user
```

### Model Inputs

The model uses:

1. **Image Location** (lat/lon from coordinates.csv)
   - Automatically looked up from image name

2. **Terrain Features** (from mtbs_dataset.csv)
   - Elevation, slope, aspect, NDVI, land cover
   - Looked up using nearest-neighbor matching

3. **Weather Data** (from user input)
   - **Day 0** (ignition day):
     - Temperature, humidity, precipitation, soil moisture
     - Wind speed, gust, direction
   - **Day 3** (3 days after):
     - Same parameters (assumed to represent post-ignition conditions)

### Model Output

- **predicted_acres** — Estimated acres burned
- **log_acres** — Log-scale prediction (debugging info)

## API Endpoint

**POST http://localhost:5000/predict**

### Request Format

```json
{
  "image_name": "20562846.png",
  "day0": {
    "temp_c": 28,
    "humidity_pct": 35,
    "precip_mm": 0,
    "soil_moisture_pct": 20,
    "wind_speed_kmh": 15,
    "wind_gust_kmh": 35,
    "wind_direction_deg": 270
  },
  "day3": {
    "temp_c": 32,
    "humidity_pct": 25,
    "precip_mm": 0,
    "soil_moisture_pct": 15,
    "wind_speed_kmh": 20,
    "wind_gust_kmh": 45,
    "wind_direction_deg": 280
  }
}
```

### Response Format

```json
{
  "predicted_acres": 1234.56,
  "log_acres": 3.21,
  "error": null
}
```

## Troubleshooting

### "Model not found" Error

- Run `python non-image-model.py` first to train and save the model
- Ensure `wildfire_model.pkl` exists in the same folder as `server.py`

### "Image not found in coordinates.csv"

- Verify the image name matches exactly (case-sensitive)
- Check `coordinates.csv` has the image listed

### "Could not reach prediction server"

- Ensure `python server.py` is running in another terminal
- Check that port 5000 is not in use: `netstat -an | grep 5000`
- If needed, change port in `server.py` and `prediction-client.js`

### CORS Errors

If you get CORS errors, install Flask-CORS:

```bash
pip install flask-cors
```

Then update server.py:

```python
from flask_cors import CORS
CORS(app)
```

## Performance Notes

- **Training**: ~5-10 minutes (one-time)
- **Prediction**: < 100ms per request
- **Model size**: ~50-100 MB (wildfire_model.pkl)

## Next Steps

1. ✅ Refactored model for inference
2. ✅ Built prediction API
3. ✅ Integrated with website
4. [ ] Add result visualization (fire size map)
5. [ ] Add multiple fire scenarios
6. [ ] Deploy to cloud (AWS/GCP)
