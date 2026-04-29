import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import os

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split

# Import the refactored model functions
from model import engineer_features, MODEL_PATH, DATASET_PATH

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(
        f"Dataset not found: {DATASET_PATH}. Place the CSV in the project root."
    )

df = pd.read_csv(DATASET_PATH)

df = df.dropna(subset=["acres_burned"])

# Target engineering: clip extreme fires, then log1p + quantile transform
from sklearn.preprocessing import QuantileTransformer

clip_max = df["acres_burned"].quantile(0.995)
df["acres_burned_clipped"] = df["acres_burned"].clip(upper=clip_max)

df["log_acres"] = np.log1p(df["acres_burned_clipped"])

qt = QuantileTransformer(output_distribution="normal", random_state=42)
df["target_qt"] = qt.fit_transform(df[["log_acres"]])

# Feature Engineering (using refactored function)
df = engineer_features(df)


features = [

    # ── Location & terrain (top raw correlators) ─────────────────────────────
    "lat",
    "lon",                           # r=0.25, 0.34 — geography matters a lot
    "elevation_m",                          # r=0.23
    "slope_deg",                            # r=0.18
    "aspect_sin", "aspect_cos",             # low raw r, but used in compounds

    # ── Vegetation & land ────────────────────────────────────────────────────
    "ndvi",                                 # low raw r but critical in compounds
    "land_cover",                           # low raw r but kept for tree splits

    # ── Seasonality ──────────────────────────────────────────────────────────
    "day_of_year",
    "peak_fire_season",

    # ── Pre-ignition moisture conditions (7-day prior) ───────────────────────
    "rh_min_7d_prior (%)",                  # r=0.16
    "precip_7d_prior (mm)",                 # r=0.13
    "soil_moisture_7d_prior_avg (m³/m³)",   # r=0.10
    "temp_max_7d_prior (°C)",               # r=0.06

    # ── Day -1 (most recent pre-fire fuel state) ──────────────────────────────
    "rh_min_d_minus1 (%)",                  # r=0.15 — strongest single-day pre-fire signal
    "temp_max_d_minus1 (°C)",               # r=0.10
    "soil_moisture_avg_d_minus1 (m³/m³)",   # r=0.09
    "wind_gust_max_d_minus1 (km/h)",        # r=0.05 — weak alone, useful in compounds
    "precip_sum_d_minus1 (mm)",             # r=0.03

    # ── Ignition day (2 PM snapshot) ─────────────────────────────────────────
    "rh_ign_1400 (%)",                      # r=0.15
    "temp_ign_1400 (°C)",                   # r=0.08
    "soil_moisture_ign_1400 (m³/m³)",       # r=0.08
    "wind_gust_ign_1400 (km/h)",            # r=0.05
    "wind_speed_ign_1400 (km/h)",           # r=0.01 (kept for gust ratio)

    # ── Post-ignition daily (D+1 to D+3) — RH is the star here ──────────────
    "rh_min_d_plus1 (%)",                   # r=0.18
    "rh_min_d_plus2 (%)",                   # r=0.19
    "rh_min_d_plus3 (%)",                   # r=0.20 — strongest of all RH features
    # "precip_sum_d_plus1 (mm)",              # r=0.09
    # "precip_sum_d_plus2 (mm)",              # r=0.12
    # "precip_sum_d_plus3 (mm)",              # r=0.12
    "wind_speed_max_d_plus1 (km/h)",        # r=0.06
    "wind_speed_max_d_plus2 (km/h)",        # r=0.07
    "wind_speed_max_d_plus3 (km/h)",        # r=0.07

    # ── Post-ignition aggregates (30d) ────────────────────────────────────────
    "precip_30d_post (mm)",                 # r=0.22 — 2nd strongest overall
    "rh_min_30d_post (%)",                  # r=0.15
    "wind_speed_max_30d_post (km/h)",       # r=0.12

    # ── Ignition-day engineered compounds ────────────────────────────────────
    "fire_risk_index",                      # wind × (100 - rh)
    "fuel_dryness",                         # (1-ndvi) / soil
    "hot_dry_windy",                        # wind × dryness × fuel
    "terrain_wind",                         # wind × upslope aspect
    "gust_to_wind_ratio",                   # turbulence proxy
    "wind_slope_alignment",                 # upslope wind advantage
    # "dry_windy_flag",                       # binary extreme conditions

    # ── Pre-ignition trend compounds (NEW) ────────────────────────────────────
    "rh_drying_trend",                      # getting drier toward ignition?
    "temp_heating_trend",                   # getting hotter toward ignition?
    # "pre_fire_stress",                      # combined drying + heating + no rain
    "fuel_dryness_d_minus1",                # D-1 fuel dryness (fresher than ign day)

    # ── Post-ignition spread compounds (NEW) ──────────────────────────────────
    "min_rh_3d_post",                       # worst dryness in spread window
    "max_gust_3d_post",                     # worst wind in spread window
    "max_temp_3d_post",                     # worst heat in spread window
    "precip_3d_post",                       # total suppression rain
    "spread_danger_index",                  # compound: wind × dryness × fuel post-ign
    "post_rh_drop",                         # did it get drier after ignition?
    "precip_change_post_vs_prior",          # rain change pre→post ignition
    "soil_drying_post",                     # soil losing moisture as fire burns

    #Other
    "extreme_fire_combo",
    "heat_wind_combo",
    "dryness_explosion",
    "fire_acceleration",
    "wind_fire_drive",
    "heat_dryness_post",
    "bad_conditions_persistence",
    "dry_windy_persistence",
    "terrain_fire_amplification",
    "fuel_wind_dryness",
    "shock_index"
]


# Keep only available columns
features = [f for f in features if f in df.columns]


X = df[features]
y = df["target_qt"]

# RandomForest Regression

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


model = RandomForestRegressor(
    n_estimators=600,
    max_depth=12,
    min_samples_leaf=8,
    random_state=42,
    n_jobs=-1
)

# Sample weighting: down-weight extremely large fires
sample_weights = 1 / (1 + df.loc[X.index, "acres_burned_clipped"])
weights_train = sample_weights.loc[X_train.index]

model.fit(X_train, y_train, sample_weight=weights_train)

pred_qt = model.predict(X_test)

# Convert back to acres
pred_log = qt.inverse_transform(pred_qt.reshape(-1, 1)).ravel()
pred_acres = np.expm1(pred_log)
true_log = qt.inverse_transform(y_test.to_numpy().reshape(-1, 1)).ravel()
true_acres = np.expm1(true_log)

print("R^2 (log scale):", r2_score(y_test, pred_log))
print("MAE (log scale):", mean_absolute_error(y_test, pred_log))

print("\n--- REAL WORLD METRICS ---")
print("MAE (acres):", mean_absolute_error(true_acres, pred_acres))
print("RMSE (acres):", np.sqrt(mean_squared_error(true_acres, pred_acres)))

importances = model.feature_importances_

show_plots = os.environ.get("NO_PLOTS", "").lower() not in {"1", "true", "yes"}

if show_plots:
    plt.figure(figsize=(8,8))
    plt.barh(features, importances)
    plt.title("Feature Importance")
    plt.xlabel("Importance")
    plt.show()

    plt.scatter(true_acres, pred_acres, alpha=0.5)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("True Acres")
    plt.ylabel("Predicted Acres")
    plt.title("Prediction vs True (Log Scale)")
    plt.show()

# ============================================
# Show 5 random fires (Actual vs Predicted)
# ============================================

# Create a dataframe for comparison
results_df = X_test.copy()
results_df["true_acres"] = true_acres
results_df["pred_acres"] = pred_acres

# Optional: include log values too
results_df["true_log"] = true_log
results_df["pred_log"] = pred_log

# Sample 5 random fires
sample = results_df.sample(20, random_state=None)

print("\n===== 20 RANDOM FIRE PREDICTIONS =====\n")

for i, row in sample.iterrows():
    print(f"Fire Index: {i}")
    print(f"Actual Acres:    {row['true_acres']:.2f}")
    print(f"Predicted Acres: {row['pred_acres']:.2f}")
    print(f"Error:           {abs(row['true_acres'] - row['pred_acres']):.2f}")
    print("-" * 40)

# ============================================
# Save trained model for later use
# ============================================

print(f"\nSaving model to {MODEL_PATH}...")
model_bundle = {
    "model": model,
    "y_transformer": qt,
    "target_mode": "log1p+quantile",
    "clip_max": float(clip_max),
}
joblib.dump(model_bundle, MODEL_PATH)
print(f"Model saved successfully!")

print("\n✓ Training complete. Model is ready for predictions via model.predict_acres_burned()")