/**
 * Wildfire Prediction - JavaScript integration
 * 
 * Usage:
 * Include this file after app.js
 * Call: submitWeatherDataForPrediction(imageName) after collecting weather data
 */

// Store the current image name globally so we can use it for predictions
let currentImageName = null;

/**
 * Called when user selects an image
 * Save the image name for later use in prediction
 */
function setCurrentImage(imageName) {
  currentImageName = imageName;
}

/**
 * Convert weatherData object to API format
 */
function formatWeatherForAPI() {
  return {
    image_name: currentImageName,
    day0: {
      temp_c: weatherData.day0.temperature || 25,
      humidity_pct: weatherData.day0.humidity || 50,
      precip_mm: weatherData.day0.precipitation || 0,
      soil_moisture_pct: weatherData.day0.soilMoisture || 50,
      wind_speed_kmh: weatherData.day0.windSpeed || 10,
      wind_gust_kmh: weatherData.day0.windGust || 15,
      wind_direction_deg: weatherData.day0.windDirection || 0
    },
    day3: {
      temp_c: weatherData.day3.temperature || 25,
      humidity_pct: weatherData.day3.humidity || 50,
      precip_mm: weatherData.day3.precipitation || 0,
      soil_moisture_pct: weatherData.day3.soilMoisture || 50,
      wind_speed_kmh: weatherData.day3.windSpeed || 10,
      wind_gust_kmh: weatherData.day3.windGust || 15,
      wind_direction_deg: weatherData.day3.windDirection || 0
    }
  };
}

/**
 * Submit weather data to prediction API
 * Called when user clicks done after filling day3 weather
 */
async function submitWeatherDataForPrediction() {
  if (!currentImageName) {
    console.error("No image selected for prediction");
    return;
  }

  const payload = formatWeatherForAPI();

  try {
    console.log("Sending prediction request:", payload);

    const response = await fetch("http://localhost:5000/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("Prediction failed:", error);
      alert(`Error: ${error.error}`);
      return;
    }

    const result = await response.json();
    console.log("Prediction result:", result);

    // Display result to user
    displayPredictionResult(result);
    submitImagePrediction();
  } catch (error) {
    console.error("Network error:", error);
    alert(
      "Network error: Could not reach prediction server. Is server.py running?"
    );
  }
}

async function submitImagePrediction() {
  if (!currentImageName || typeof getFireMaskDataUrl !== "function") {
    return;
  }

  const maskDataUrl = getFireMaskDataUrl();
  if (!maskDataUrl) {
    return;
  }

  try {
    const response = await fetch("http://localhost:5000/predict-image", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        image_name: currentImageName,
        mask_png: maskDataUrl,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("Image prediction failed:", error);
      return;
    }

    const result = await response.json();
    if (result.overlay_png && typeof showPredictionImage === "function") {
      showPredictionImage(result.overlay_png);
    }
  } catch (error) {
    console.error("Network error (image prediction):", error);
  }
}

/**
 * Display prediction result to user
 */
function displayPredictionResult(result) {
  const output = document.getElementById("prediction-output");
  if (output) {
    const acres = result.predicted_acres.toFixed(2);
    output.innerHTML = `acres burned: <span>${acres}</span>`;
    output.classList.remove("is-hidden");
  }

  // Optionally, log to console for debugging
  console.log("Full prediction data:", result);
}
