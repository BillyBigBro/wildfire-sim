"""
Flask API server for wildfire prediction.
Accepts weather data + image location and returns predicted acres burned.

Run with: python server.py
Then access from frontend at: http://localhost:5000/predict
"""

from flask import Flask, request, jsonify
import csv
import os
from model import predict_acres_burned

app = Flask(__name__)

# Path to coordinates CSV (from the website)
COORDINATES_CSV = "coordinates.csv"


def get_image_coordinates(image_name):
    """
    Look up latitude and longitude for an image from coordinates.csv
    """
    if not os.path.exists(COORDINATES_CSV):
        return None, None
    
    with open(COORDINATES_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("image_name") == image_name:
                try:
                    lat = float(row.get("latitude", 0))
                    lon = float(row.get("longitude", 0))
                    return lat, lon
                except (ValueError, TypeError):
                    return None, None
    
    return None, None


@app.route("/predict", methods=["POST"])
def predict():
    """
    Predict wildfire acres burned.
    
    Expects JSON:
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
    
    Returns JSON:
    {
      "predicted_acres": 1234.56,
      "log_acres": 3.21,
      "error": null
    }
    """
    
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        image_name = data.get("image_name")
        day0 = data.get("day0")
        day3 = data.get("day3")
        
        if not all([image_name, day0, day3]):
            return jsonify({"error": "Missing required fields: image_name, day0, day3"}), 400
        
        # Get image coordinates
        lat, lon = get_image_coordinates(image_name)
        if lat is None or lon is None:
            return jsonify({"error": f"Image '{image_name}' not found in coordinates.csv"}), 404
        
        # Make prediction
        result = predict_acres_burned(lat, lon, day0, day3)
        
        if result.get("error"):
            return jsonify(result), 500
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    print("Starting Wildfire Prediction API server...")
    print("Server running on http://localhost:5000")
    print("Health check: http://localhost:5000/health")
    print("Prediction endpoint: POST http://localhost:5000/predict")
    app.run(debug=True, port=5000)
