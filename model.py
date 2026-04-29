"""
Wildfire prediction model with training and inference capabilities.
Accepts weather data + image location to predict acres burned.
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import os

# ============================================================================
# GLOBAL CONSTANTS AND DATA LOADING
# ============================================================================

# Path to the full dataset with terrain and weather features
DATASET_PATH = "mtbs_dataset(GoogleEarth+OpenMeteo).csv"
MODEL_PATH = "wildfire_model.pkl"
TERRAIN_CACHE = None  # Will be loaded once


def load_terrain_data():
    """Load the full MTBS dataset (once) for terrain lookups."""
    global TERRAIN_CACHE
    if TERRAIN_CACHE is None:
        if os.path.exists(DATASET_PATH):
            TERRAIN_CACHE = pd.read_csv(DATASET_PATH)
        else:
            print(f"Warning: {DATASET_PATH} not found. Terrain lookups will fail.")
            TERRAIN_CACHE = pd.DataFrame()
    return TERRAIN_CACHE


def get_terrain_for_location(lat, lon, tolerance=0.5):
    """
    Find terrain features (elevation, slope, aspect, ndvi, etc.) for a given lat/lon.
    Uses nearest-neighbor matching within tolerance.
    """
    terrain_df = load_terrain_data()
    
    if terrain_df.empty:
        # Return default/neutral terrain values
        return {
            "elevation_m": 1000,
            "slope_deg": 15,
            "aspect_sin": 0.5,
            "aspect_cos": 0.5,
            "ndvi": 0.5,
            "land_cover": 1,
        }
    
    # Find nearest location in the dataset
    terrain_df["distance"] = np.sqrt(
        (terrain_df["lat"] - lat)**2 + (terrain_df["lon"] - lon)**2
    )
    
    nearest = terrain_df.nsmallest(1, "distance")
    
    if nearest.empty or nearest["distance"].iloc[0] > tolerance:
        # Location not found; use defaults
        return {
            "elevation_m": 1000,
            "slope_deg": 15,
            "aspect_sin": 0.5,
            "aspect_cos": 0.5,
            "ndvi": 0.5,
            "land_cover": 1,
        }
    
    row = nearest.iloc[0]
    return {
        "elevation_m": row.get("elevation_m", 1000),
        "slope_deg": row.get("slope_deg", 15),
        "aspect_sin": row.get("aspect_sin", 0.5),
        "aspect_cos": row.get("aspect_cos", 0.5),
        "ndvi": row.get("ndvi", 0.5),
        "land_cover": row.get("land_cover", 1),
    }


# ============================================================================
# FEATURE ENGINEERING (Reusable for both training and prediction)
# ============================================================================

def engineer_features(df):
    """
    Apply all feature engineering transformations to a dataframe.
    Expects columns: temperature, humidity, precipitation, soil_moisture, 
    wind_speed, wind_gust, wind_direction, elevation_m, slope_deg, etc.
    """
    
    df = df.copy()
    
    # Basic temporal features (placeholder; adjust if actual dates provided)
    if "ignition_date" in df.columns:
        df["ignition_date"] = pd.to_datetime(df["ignition_date"], errors="coerce")
        df["day_of_year"] = df["ignition_date"].dt.dayofyear
    else:
        df["day_of_year"] = 180  # Default mid-year
    
    df["peak_fire_season"] = ((df.get("day_of_year", 180) >= 180) & 
                               (df.get("day_of_year", 180) <= 273)).astype(int)
    
    # Wind direction conversions
    if "wind_direction_ign_1400 (°)" in df.columns:
        df["wind_dir_ign_rad"] = np.deg2rad(df["wind_direction_ign_1400 (°)"])
        df["wind_dir_ign_sin"] = np.sin(df["wind_dir_ign_rad"])
        df["wind_dir_ign_cos"] = np.cos(df["wind_dir_ign_rad"])
    
    # Ignition-day compounds
    if "wind_gust_ign_1400 (km/h)" in df.columns and "rh_ign_1400 (%)" in df.columns:
        df["fire_risk_index"] = (
            df["wind_gust_ign_1400 (km/h)"] * (100 - df["rh_ign_1400 (%)"])
        )
    
    if "ndvi" in df.columns and "soil_moisture_ign_1400 (m³/m³)" in df.columns:
        df["fuel_dryness"] = (
            (1 - df["ndvi"]) / (df["soil_moisture_ign_1400 (m³/m³)"] + 0.01)
        )
    
    if "wind_gust_ign_1400 (km/h)" in df.columns and "rh_ign_1400 (%)" in df.columns and "ndvi" in df.columns:
        df["hot_dry_windy"] = (
            df["wind_gust_ign_1400 (km/h)"] *
            (100 - df["rh_ign_1400 (%)"]) *
            (1 - df["ndvi"])
        )
    
    if "wind_gust_ign_1400 (km/h)" in df.columns and "aspect_cos" in df.columns:
        df["terrain_wind"] = df["wind_gust_ign_1400 (km/h)"] * df["aspect_cos"]
    
    if "wind_gust_ign_1400 (km/h)" in df.columns and "wind_speed_ign_1400 (km/h)" in df.columns:
        df["gust_to_wind_ratio"] = (
            df["wind_gust_ign_1400 (km/h)"] /
            (df["wind_speed_ign_1400 (km/h)"] + 0.1)
        )
    
    if "wind_dir_ign_cos" in df.columns and "aspect_cos" in df.columns and "wind_dir_ign_sin" in df.columns and "aspect_sin" in df.columns:
        df["wind_slope_alignment"] = (
            df["wind_dir_ign_cos"] * df["aspect_cos"] +
            df["wind_dir_ign_sin"] * df["aspect_sin"]
        )
    
    # Pre-ignition trends
    if "rh_min_7d_prior (%)" in df.columns and "rh_min_d_minus1 (%)" in df.columns:
        df["rh_drying_trend"] = df["rh_min_7d_prior (%)"] - df["rh_min_d_minus1 (%)"]
    
    if "temp_max_d_minus1 (°C)" in df.columns and "temp_max_7d_prior (°C)" in df.columns:
        df["temp_heating_trend"] = (
            df["temp_max_d_minus1 (°C)"] - df["temp_max_7d_prior (°C)"]
        )
    
    if "soil_moisture_avg_d_minus1 (m³/m³)" in df.columns and "ndvi" in df.columns:
        df["fuel_dryness_d_minus1"] = (
            (1 - df["ndvi"]) / (df["soil_moisture_avg_d_minus1 (m³/m³)"] + 0.01)
        )
    
    # Post-ignition aggregates (3-day window)
    min_rh_cols = ["rh_min_d_plus1 (%)", "rh_min_d_plus2 (%)", "rh_min_d_plus3 (%)"]
    if all(col in df.columns for col in min_rh_cols):
        df["min_rh_3d_post"] = df[min_rh_cols].min(axis=1)
    
    max_gust_cols = ["wind_gust_max_d_plus1 (km/h)", "wind_gust_max_d_plus2 (km/h)", "wind_gust_max_d_plus3 (km/h)"]
    if all(col in df.columns for col in max_gust_cols):
        df["max_gust_3d_post"] = df[max_gust_cols].max(axis=1)
    
    max_temp_cols = ["temp_max_d_plus1 (°C)", "temp_max_d_plus2 (°C)", "temp_max_d_plus3 (°C)"]
    if all(col in df.columns for col in max_temp_cols):
        df["max_temp_3d_post"] = df[max_temp_cols].max(axis=1)
    
    precip_cols = ["precip_sum_d_plus1 (mm)", "precip_sum_d_plus2 (mm)", "precip_sum_d_plus3 (mm)"]
    if all(col in df.columns for col in precip_cols):
        df["precip_3d_post"] = df[precip_cols].sum(axis=1)
    
    # Post-ignition compounds
    if "max_gust_3d_post" in df.columns and "min_rh_3d_post" in df.columns and "ndvi" in df.columns:
        df["spread_danger_index"] = (
            df["max_gust_3d_post"] *
            (100 - df["min_rh_3d_post"]) *
            (1 - df["ndvi"])
        )
    
    if "rh_min_d_minus1 (%)" in df.columns and "min_rh_3d_post" in df.columns:
        df["post_rh_drop"] = df["rh_min_d_minus1 (%)"] - df["min_rh_3d_post"]
    
    if "precip_7d_prior (mm)" in df.columns and "precip_3d_post" in df.columns:
        df["precip_change_post_vs_prior"] = df["precip_3d_post"] - df["precip_7d_prior (mm)"]
    
    soil_cols = ["soil_moisture_avg_d_plus1 (m³/m³)", "soil_moisture_avg_d_plus2 (m³/m³)", "soil_moisture_avg_d_plus3 (m³/m³)"]
    if "soil_moisture_avg_d_minus1 (m³/m³)" in df.columns and all(col in df.columns for col in soil_cols):
        df["soil_drying_post"] = (
            df["soil_moisture_avg_d_minus1 (m³/m³)"] -
            df[soil_cols].mean(axis=1)
        )
    
    # Additional compounds
    if "max_temp_3d_post" in df.columns and "max_gust_3d_post" in df.columns and "min_rh_3d_post" in df.columns:
        df["extreme_fire_combo"] = (
            df["max_temp_3d_post"] *
            df["max_gust_3d_post"] /
            (df["min_rh_3d_post"] + 1)
        )
    
    if "temp_ign_1400 (°C)" in df.columns and "wind_gust_ign_1400 (km/h)" in df.columns:
        df["heat_wind_combo"] = (
            df["temp_ign_1400 (°C)"] * df["wind_gust_ign_1400 (km/h)"]
        )
    
    if "rh_ign_1400 (%)" in df.columns and "ndvi" in df.columns:
        df["dryness_explosion"] = (
            (100 - df["rh_ign_1400 (%)"]) * (1 - df["ndvi"])
        )
    
    if "max_temp_3d_post" in df.columns and "max_gust_3d_post" in df.columns and "min_rh_3d_post" in df.columns:
        df["fire_acceleration"] = (
            df["max_temp_3d_post"] *
            df["max_gust_3d_post"] *
            (100 - df["min_rh_3d_post"])
        )
    
    if "max_gust_3d_post" in df.columns and "min_rh_3d_post" in df.columns:
        df["wind_fire_drive"] = (
            df["max_gust_3d_post"] / (df["min_rh_3d_post"] + 1)
        )
    
    if "max_temp_3d_post" in df.columns and "min_rh_3d_post" in df.columns:
        df["heat_dryness_post"] = (
            df["max_temp_3d_post"] * (100 - df["min_rh_3d_post"])
        )
    
    rh_cols = ["rh_min_d_plus1 (%)", "rh_min_d_plus2 (%)", "rh_min_d_plus3 (%)"]
    if all(col in df.columns for col in rh_cols):
        df["bad_conditions_persistence"] = df[rh_cols].sum(axis=1)
    
    if "max_gust_3d_post" in df.columns and "bad_conditions_persistence" in df.columns:
        df["dry_windy_persistence"] = (
            df["max_gust_3d_post"] *
            (300 - df["bad_conditions_persistence"])
        )
    
    if "slope_deg" in df.columns and "max_gust_3d_post" in df.columns and "ndvi" in df.columns:
        df["terrain_fire_amplification"] = (
            df["slope_deg"] *
            df["max_gust_3d_post"] *
            (1 - df["ndvi"])
        )
    
    if "ndvi" in df.columns and "max_gust_3d_post" in df.columns and "min_rh_3d_post" in df.columns:
        df["fuel_wind_dryness"] = (
            (1 - df["ndvi"]) *
            df["max_gust_3d_post"] *
            (100 - df["min_rh_3d_post"])
        )
    
    if "rh_min_d_minus1 (%)" in df.columns and "min_rh_3d_post" in df.columns and "max_temp_3d_post" in df.columns and "temp_max_d_minus1 (°C)" in df.columns:
        df["shock_index"] = (
            (df["rh_min_d_minus1 (%)"] - df["min_rh_3d_post"]) *
            (df["max_temp_3d_post"] - df["temp_max_d_minus1 (°C)"])
        )
    
    return df


# ============================================================================
# PREDICTION FROM USER INPUT
# ============================================================================

def build_prediction_input(lat, lon, day0_weather, day3_weather, ignition_date=None):
    """
    Build a prediction input row from:
    - lat, lon: Image location
    - day0_weather: dict with temp_c, humidity_pct, precip_mm, soil_moisture_pct, 
                    wind_speed_kmh, wind_gust_kmh, wind_direction_deg
    - day3_weather: same structure for day 3
    - ignition_date: optional datetime for temporal features
    
    Returns: DataFrame row ready for feature engineering and prediction
    """
    
    # Get terrain data for location
    terrain = get_terrain_for_location(lat, lon)
    
    # Build base feature dict
    features_dict = {
        "lat": lat,
        "lon": lon,
        "elevation_m": terrain["elevation_m"],
        "slope_deg": terrain["slope_deg"],
        "aspect_sin": terrain["aspect_sin"],
        "aspect_cos": terrain["aspect_cos"],
        "ndvi": terrain["ndvi"],
        "land_cover": terrain["land_cover"],
        "ignition_date": ignition_date or pd.Timestamp.now(),
    }
    
    # Day 0 (ignition day) features - map user inputs to model columns
    features_dict.update({
        "temp_ign_1400 (°C)": day0_weather.get("temp_c", 25),
        "rh_ign_1400 (%)": day0_weather.get("humidity_pct", 50),
        "soil_moisture_ign_1400 (m³/m³)": day0_weather.get("soil_moisture_pct", 50) / 100,
        "wind_speed_ign_1400 (km/h)": day0_weather.get("wind_speed_kmh", 10),
        "wind_gust_ign_1400 (km/h)": day0_weather.get("wind_gust_kmh", 15),
        "wind_direction_ign_1400 (°)": day0_weather.get("wind_direction_deg", 0),
        "precip_sum_d_minus1 (mm)": day0_weather.get("precip_mm", 0),
        
        # Pre-ignition (use day0 as proxy for prior conditions)
        "rh_min_7d_prior (%)": day0_weather.get("humidity_pct", 50),
        "rh_min_d_minus1 (%)": day0_weather.get("humidity_pct", 50),
        "temp_max_d_minus1 (°C)": day0_weather.get("temp_c", 25),
        "temp_max_7d_prior (°C)": day0_weather.get("temp_c", 25),
        "soil_moisture_avg_d_minus1 (m³/m³)": day0_weather.get("soil_moisture_pct", 50) / 100,
        "soil_moisture_7d_prior_avg (m³/m³)": day0_weather.get("soil_moisture_pct", 50) / 100,
        "wind_gust_max_d_minus1 (km/h)": day0_weather.get("wind_gust_kmh", 15),
        "precip_7d_prior (mm)": day0_weather.get("precip_mm", 0),
        "precip_sum_d_minus1 (mm)": day0_weather.get("precip_mm", 0),
    })
    
    # Day 3 (post-ignition) features - map day3 inputs across d_plus1, d_plus2, d_plus3
    # Assume day3 conditions represent the worst-case across the 3-day window
    features_dict.update({
        "rh_min_d_plus1 (%)": day3_weather.get("humidity_pct", 50),
        "rh_min_d_plus2 (%)": day3_weather.get("humidity_pct", 50),
        "rh_min_d_plus3 (%)": day3_weather.get("humidity_pct", 50),
        "temp_max_d_plus1 (°C)": day3_weather.get("temp_c", 25),
        "temp_max_d_plus2 (°C)": day3_weather.get("temp_c", 25),
        "temp_max_d_plus3 (°C)": day3_weather.get("temp_c", 25),
        "wind_gust_max_d_plus1 (km/h)": day3_weather.get("wind_gust_kmh", 15),
        "wind_gust_max_d_plus2 (km/h)": day3_weather.get("wind_gust_kmh", 15),
        "wind_gust_max_d_plus3 (km/h)": day3_weather.get("wind_gust_kmh", 15),
        "wind_speed_max_d_plus1 (km/h)": day3_weather.get("wind_speed_kmh", 10),
        "wind_speed_max_d_plus2 (km/h)": day3_weather.get("wind_speed_kmh", 10),
        "wind_speed_max_d_plus3 (km/h)": day3_weather.get("wind_speed_kmh", 10),
        "soil_moisture_avg_d_plus1 (m³/m³)": day3_weather.get("soil_moisture_pct", 50) / 100,
        "soil_moisture_avg_d_plus2 (m³/m³)": day3_weather.get("soil_moisture_pct", 50) / 100,
        "soil_moisture_avg_d_plus3 (m³/m³)": day3_weather.get("soil_moisture_pct", 50) / 100,
        "precip_sum_d_plus1 (mm)": day3_weather.get("precip_mm", 0),
        "precip_sum_d_plus2 (mm)": day3_weather.get("precip_mm", 0),
        "precip_sum_d_plus3 (mm)": day3_weather.get("precip_mm", 0),
        
        # 30-day post-ignition (use day3 as proxy)
        "precip_30d_post (mm)": day3_weather.get("precip_mm", 0) * 10,  # Scale up as approximation
        "rh_min_30d_post (%)": day3_weather.get("humidity_pct", 50),
        "wind_speed_max_30d_post (km/h)": day3_weather.get("wind_speed_kmh", 10),
    })
    
    return pd.DataFrame([features_dict])


def predict_acres_burned(lat, lon, day0_weather, day3_weather, model_path=MODEL_PATH):
    """
    Predict acres burned given image location and weather data.
    
    Args:
        lat, lon: Image coordinates
        day0_weather: dict with keys: temp_c, humidity_pct, precip_mm, soil_moisture_pct, 
                      wind_speed_kmh, wind_gust_kmh, wind_direction_deg
        day3_weather: same structure for 3 days after ignition
        model_path: path to saved model
    
    Returns:
        dict with predicted_acres, log_acres, confidence
    """
    
    # Load model
    if not os.path.exists(model_path):
        return {
            "error": f"Model not found at {model_path}. Train and save the model first.",
            "predicted_acres": None,
        }
    
    loaded = joblib.load(model_path)
    if isinstance(loaded, dict) and "model" in loaded:
        model = loaded["model"]
        y_transformer = loaded.get("y_transformer")
    else:
        model = loaded
        y_transformer = None
    
    # Build prediction input
    X = build_prediction_input(lat, lon, day0_weather, day3_weather)
    
    # Apply feature engineering
    X = engineer_features(X)
    
    # Select features (must match training features)
    if hasattr(model, "feature_names_in_"):
        features = list(model.feature_names_in_)
    else:
        features = [
            "lat", "lon", "elevation_m", "slope_deg", "aspect_sin", "aspect_cos",
            "ndvi", "land_cover", "day_of_year", "peak_fire_season",
            "rh_min_7d_prior (%)", "precip_7d_prior (mm)", "soil_moisture_7d_prior_avg (m³/m³)",
            "temp_max_7d_prior (°C)", "rh_min_d_minus1 (%)", "temp_max_d_minus1 (°C)",
            "soil_moisture_avg_d_minus1 (m³/m³)", "wind_gust_max_d_minus1 (km/h)",
            "precip_sum_d_minus1 (mm)", "rh_ign_1400 (%)", "temp_ign_1400 (°C)",
            "soil_moisture_ign_1400 (m³/m³)", "wind_gust_ign_1400 (km/h)",
            "wind_speed_ign_1400 (km/h)", "rh_min_d_plus1 (%)", "rh_min_d_plus2 (%)",
            "rh_min_d_plus3 (%)", "wind_speed_max_d_plus1 (km/h)", "wind_speed_max_d_plus2 (km/h)",
            "wind_speed_max_d_plus3 (km/h)", "precip_30d_post (mm)", "rh_min_30d_post (%)",
            "wind_speed_max_30d_post (km/h)", "fire_risk_index", "fuel_dryness",
            "hot_dry_windy", "terrain_wind", "gust_to_wind_ratio", "wind_slope_alignment",
            "rh_drying_trend", "temp_heating_trend", "fuel_dryness_d_minus1",
            "min_rh_3d_post", "max_gust_3d_post", "max_temp_3d_post", "precip_3d_post",
            "spread_danger_index", "post_rh_drop", "precip_change_post_vs_prior",
            "soil_drying_post", "extreme_fire_combo", "heat_wind_combo", "dryness_explosion",
            "fire_acceleration", "wind_fire_drive", "heat_dryness_post",
            "bad_conditions_persistence", "dry_windy_persistence", "terrain_fire_amplification",
            "fuel_wind_dryness", "shock_index"
        ]
    
    # Keep only features that exist
    available_features = [f for f in features if f in X.columns]
    X_pred = X[available_features]
    
    # Handle any missing features with zeros
    for f in features:
        if f not in X_pred.columns:
            X_pred[f] = 0
    
    X_pred = X_pred[features]
    
    # Predict
    pred_value = model.predict(X_pred)[0]

    if y_transformer is not None:
        log_acres_pred = y_transformer.inverse_transform(
            np.array([[pred_value]])
        ).ravel()[0]
        acres_pred = np.expm1(log_acres_pred)
    else:
        log_acres_pred = pred_value
        acres_pred = 10**log_acres_pred - 1
    
    return {
        "predicted_acres": max(0, acres_pred),
        "log_acres": log_acres_pred,
        "error": None,
    }
