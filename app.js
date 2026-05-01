const titleEl = document.getElementById("page-title");
const selectEl = document.getElementById("state-select");
const resultsEl = document.getElementById("results");

const ALLOWED_IMAGES = new Set([
  "21693566.png",
  "21748801.png",
  "21751303.png",
  "21751305.png",
  "21751309.png",
  "21804582.png",
  "21804884.png",
  "21804985.png",
  "21889717.png",
  "21889750.png",
  "21889763.png",
  "21889779.png",
  "21889943.png",
  "21889953.png",
  "21889992.png",
  "21889994.png",
  "21890003.png",
  "21890009.png",
  "21890013.png",
  "21890024.png",
  "21890056.png",
  "21890072.png",
  "21890160.png",
  "21890502.png",
  "21890524.png",
  "21997770.png",
  "21997828.png",
  "21998023.png",
  "21998095.png",
  "21998230.png",
  "21998264.png",
  "21998287.png",
  "21998313.png",
  "21999381.png",
  "22141509.png",
  "22141596.png",
  "22343661.png",
  "22343688.png",
  "22712904.png",
  "22712973.png",
  "22938749.png",
  "23036806.png",
  "23036871.png",
  "23159836.png",
  "23160475.png",
  "23300669.png",
  "23410594.png",
  "23860939.png",
  "24103557.png",
  "24103571.png",
  "24103581.png",
  "24103611.png",
  "24104631.png",
  "24191347.png",
  "24191376.png",
  "24191393.png",
  "24191418.png",
  "24191427.png",
  "24332592.png",
  "24332608.png",
  "24332622.png",
  "24332647.png",
  "24332676.png",
  "24332702.png",
  "24332704.png",
  "24332732.png",
  "24332746.png",
  "24332760.png",
  "24332763.png",
  "24332764.png",
  "24332783.png",
  "24332787.png",
  "24332801.png",
  "24332880.png",
  "24332939.png",
  "24332956.png",
  "24333000.png",
  "24333012.png",
  "24333033.png",
  "24333039.png",
  "24333270.png",
  "24333277.png",
  "24333279.png",
  "24461320.png",
  "24461328.png",
  "24461421.png",
  "24461607.png",
  "24461771.png",
  "24461899.png",
  "24461996.png",
  "24462263.png",
  "24462335.png",
  "24462488.png",
  "24462819.png",
  "24462847.png",
  "24463187.png",
  "US_2021_AZ3345510938920210616.png",
  "US_2021_AZ3368910927620210616.png",
  "US_2021_CA3451712013120211011.png",
  "US_2021_CA3568711855020210818.png",
  "US_2021_CA3604711863120210910.png",
  "US_2021_CA3627811855020210815.png",
  "US_2021_CA3658211879520210912.png",
  "US_2021_CA4086312235520210630.png",
  "US_2021_FL2521008104520210308.png",
  "US_2021_ID4453211532920210810.png",
  "US_2021_ID4558511544420210705.png",
  "US_2021_ID4663811466720210707.png",
  "US_2021_ID4762711608320210708.png",
  "US_2021_MT4568311385420210708.png",
  "US_2021_MT4579011310120210708.png",
  "US_2021_NM3340210587120210426.png",
]);

const MAX_IMAGES = 6;
const CENTER_PROMPT = "draw fire shape";

let activeTool = "brush";
let isDrawing = false;
let drawCtx = null;
let drawCanvas = null;
let snapshotStack = [];
let lastPoint = null;
let currentStrokePoints = [];
let completedStrokes = [];
let activeStageEl = null;
let activeImageWrapEl = null;
let resizeHandlerAttached = false;
let currentWeatherDay = null; // Tracks which day's weather is being entered (0 or 3)
let predictedImageEl = null;
let predictedImageWrapEl = null;

let imagesData = [];
let stateFeatures = [];
let availableStates = [];

// Weather data variables for Python script
let weatherData = {
  day0: {
    temperature: null,
    humidity: null,
    precipitation: null,
    soilMoisture: null,
    windSpeed: null,
    windGust: null,
    windDirection: null,
  },
  day3: {
    temperature: null,
    humidity: null,
    precipitation: null,
    soilMoisture: null,
    windSpeed: null,
    windGust: null,
    windDirection: null,
  },
};

const dataReady = Promise.all([
  fetch("coordinates.csv").then((response) => response.text()),
  fetch("https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json").then((response) =>
    response.json(),
  ),
])
  .then(([csvText, geoJson]) => {
    stateFeatures = geoJson.features;
    imagesData = parseCsv(csvText).filter((row) => ALLOWED_IMAGES.has(row.imageName));
    const stateSet = new Set(imagesData.map((row) => row.state).filter(Boolean));
    availableStates = Array.from(stateSet).sort();
    stateFeatures = geoJson.features.filter((feature) => stateSet.has(feature.properties.name));
    populateStateOptions(availableStates);
  })
  .catch(() => {
    resultsEl.innerHTML = '<p class="results-error">Unable to load data files.</p>';
  });

selectEl.addEventListener("change", async (event) => {
  const selectedState = event.target.value;
  if (!selectedState) {
    return;
  }

  await dataReady;

  animateTitleSwap(selectedState.toLowerCase());
  const matches = imagesData.filter((row) => row.state === selectedState);
  const chosen = shuffle(matches).slice(0, MAX_IMAGES);
  renderResults(selectedState.toLowerCase(), chosen);
});

function populateStateOptions(states) {
  selectEl.innerHTML = `
    <option value="" selected disabled>Choose a state</option>
    ${states.map((state) => `<option>${state}</option>`).join("")}
  `;
}

function parseCsv(csvText) {
  const lines = csvText.trim().split(/\r?\n/);
  const headers = lines[0].split(",");
  const imageNameIndex = headers.indexOf("image_name");
  const latIndex = headers.indexOf("latitude");
  const lonIndex = headers.indexOf("longitude");

  return lines.slice(1).map((line) => {
    const parts = line.split(",");
    const latitude = Number(parts[latIndex]);
    const longitude = Number(parts[lonIndex]);

    return {
      imageName: parts[imageNameIndex],
      latitude,
      longitude,
      latitudeText: parts[latIndex],
      longitudeText: parts[lonIndex],
      state: findStateName(longitude, latitude),
    };
  });
}

function findStateName(longitude, latitude) {
  for (const feature of stateFeatures) {
    const geometry = feature.geometry;

    if (geometry.type === "Polygon") {
      if (pointInPolygon(longitude, latitude, geometry.coordinates)) {
        return feature.properties.name;
      }
    }

    if (geometry.type === "MultiPolygon") {
      for (const polygonCoords of geometry.coordinates) {
        if (pointInPolygon(longitude, latitude, polygonCoords)) {
          return feature.properties.name;
        }
      }
    }
  }

  return null;
}

function pointInPolygon(longitude, latitude, rings) {
  if (!rings || rings.length === 0) {
    return false;
  }

  if (!isPointInRing(longitude, latitude, rings[0])) {
    return false;
  }

  for (let i = 1; i < rings.length; i += 1) {
    if (isPointInRing(longitude, latitude, rings[i])) {
      return false;
    }
  }

  return true;
}

function isPointInRing(longitude, latitude, ring) {
  let inside = false;

  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];

    const intersects = yi > latitude !== yj > latitude && longitude < ((xj - xi) * (latitude - yi)) / (yj - yi) + xi;

    if (intersects) {
      inside = !inside;
    }
  }

  return inside;
}

function animateTitleSwap(newText) {
  titleEl.classList.add("is-fading");

  window.setTimeout(() => {
    titleEl.textContent = newText;
    titleEl.classList.remove("is-fading");
  }, 220);
}

function renderResults(stateTitle, rows) {
  if (rows.length === 0) {
    resultsEl.innerHTML = `<p class="results-empty">No images available for ${stateTitle}.</p>`;
    return;
  }

  resultsEl.innerHTML = `
    <div class="results-stage" id="results-stage">
      <div class="gallery-view">
        <div class="image-box">
          <div class="image-grid">
            ${rows
              .map(
                (row, index) => `
                  <article class="image-card">
                    <button class="image-card-button" type="button" data-image-index="${index}" aria-label="Open image at ${row.latitudeText}, ${row.longitudeText}">
                      <img src="images/${row.imageName}" alt="Satellite image for ${stateTitle} at ${row.latitudeText}, ${row.longitudeText}" loading="lazy" />
                    </button>
                    <p>${row.latitudeText}, ${row.longitudeText}</p>
                  </article>
                `,
              )
              .join("")}
          </div>
        </div>
      </div>

      <section class="editor-view" id="editor-view" aria-label="Draw fire shape editor">
        <h2>${CENTER_PROMPT}</h2>
        <p class="editor-subtitle">(draw a closed shape around the ignition area)</p>
        <div class="editor-image-wrap" id="editor-image-wrap">
          <img id="editor-image" src="" alt="Selected satellite image" />
          <canvas id="draw-canvas"></canvas>
          <img id="prediction-image" class="prediction-image is-hidden" alt="Predicted fire spread overlay" />
        </div>
        <div class="editor-toolbar" role="toolbar" aria-label="Drawing tools">
          <div class="editor-tools-right">
            <button id="undo-tool" class="tool-button" type="button" aria-label="Undo last stroke">
              <img src="undo.png" alt="" />
            </button>
            <button id="done-tool" class="tool-button" type="button" aria-label="Done drawing">
              <img src="done.png" alt="" />
            </button>
          </div>
        </div>
        <p id="editor-error" class="editor-error" aria-live="polite"></p>
        <p id="prediction-output" class="prediction-output is-hidden" aria-live="polite"></p>

        <section class="weather-overlay weather-overlay-day0" id="weather-overlay-day0" aria-label="Input weather conditions for day of ignition">
          <div class="weather-panel">
            <h3>input weather conditions:</h3>
            <h4>day of ignition</h4>
            <div class="weather-grid">
              <div class="weather-col">
                <label for="temperature-day0-input">temperature (C)</label>
                <input id="temperature-day0-input" type="number" step="0.1" />

                <label for="humidity-day0-input">relative humidity (%)</label>
                <div class="slider-field">
                  <input id="humidity-day0-input" type="range" min="0" max="100" value="50" />
                  <span id="humidity-day0-value">50%</span>
                </div>

                <label for="precip-day0-input">precipitation (mm)</label>
                <input id="precip-day0-input" type="number" step="0.1" min="0" />

                <label for="soil-day0-input">soil moisture (%)</label>
                <div class="slider-field">
                  <input id="soil-day0-input" type="range" min="0" max="100" value="50" />
                  <span id="soil-day0-value">50%</span>
                </div>
              </div>

              <div class="weather-col">
                <label for="wind-speed-day0-input">wind speed (km/h)</label>
                <input id="wind-speed-day0-input" type="number" step="0.1" min="0" />

                <label for="wind-gust-day0-input">wind gust speed (km/h)</label>
                <input id="wind-gust-day0-input" type="number" step="0.1" min="0" />

                <label for="wind-direction-day0-input">wind direction (deg.)</label>
                <div class="wind-direction-picker">
                  <div id="wind-direction-day0-circle" class="wind-direction-circle" role="slider" aria-label="Wind direction day of ignition" aria-valuemin="0" aria-valuemax="359" aria-valuenow="0" tabindex="0">
                    <div id="wind-direction-day0-line" class="wind-direction-line"></div>
                    <span class="wind-direction-dot" aria-hidden="true"></span>
                  </div>
                  <span class="wind-direction-readout"><span id="wind-direction-day0-value">0</span>deg</span>
                  <input id="wind-direction-day0-input" type="hidden" value="0" />
                </div>
              </div>
            </div>
            <div class="weather-actions">
              <button id="weather-done-button-day0" type="button">done</button>
            </div>
          </div>
        </section>

        <section class="weather-overlay weather-overlay-day3" id="weather-overlay-day3" aria-label="Input weather conditions for 3 days after ignition">
          <div class="weather-panel">
            <h3>input weather conditions:</h3>
            <h4>3 days after ignition</h4>
            <div class="weather-grid">
              <div class="weather-col">
                <label for="temperature-day3-input">temperature (C)</label>
                <input id="temperature-day3-input" type="number" step="0.1" />

                <label for="humidity-day3-input">relative humidity (%)</label>
                <div class="slider-field">
                  <input id="humidity-day3-input" type="range" min="0" max="100" value="50" />
                  <span id="humidity-day3-value">50%</span>
                </div>

                <label for="precip-day3-input">precipitation (mm)</label>
                <input id="precip-day3-input" type="number" step="0.1" min="0" />

                <label for="soil-day3-input">soil moisture (%)</label>
                <div class="slider-field">
                  <input id="soil-day3-input" type="range" min="0" max="100" value="50" />
                  <span id="soil-day3-value">50%</span>
                </div>
              </div>

              <div class="weather-col">
                <label for="wind-speed-day3-input">wind speed (km/h)</label>
                <input id="wind-speed-day3-input" type="number" step="0.1" min="0" />

                <label for="wind-gust-day3-input">wind gust speed (km/h)</label>
                <input id="wind-gust-day3-input" type="number" step="0.1" min="0" />

                <label for="wind-direction-day3-input">wind direction (deg.)</label>
                <div class="wind-direction-picker">
                  <div id="wind-direction-day3-circle" class="wind-direction-circle" role="slider" aria-label="Wind direction 3 days after ignition" aria-valuemin="0" aria-valuemax="359" aria-valuenow="0" tabindex="0">
                    <div id="wind-direction-day3-line" class="wind-direction-line"></div>
                    <span class="wind-direction-dot" aria-hidden="true"></span>
                  </div>
                  <span class="wind-direction-readout"><span id="wind-direction-day3-value">0</span>deg</span>
                  <input id="wind-direction-day3-input" type="hidden" value="0" />
                </div>
              </div>
            </div>
            <div class="weather-actions">
              <button id="weather-done-button-day3" type="button">done</button>
            </div>
          </div>
        </section>
      </section>
    </div>
  `;

  const cards = [...resultsEl.querySelectorAll(".image-card")];
  cards.forEach((card, index) => {
    card.style.animationDelay = `${index * 180}ms`;
    card.classList.add("is-visible");
  });

  setupEditorInteractions(rows);
}

function setupEditorInteractions(rows) {
  const stageEl = document.getElementById("results-stage");
  const imageWrapEl = document.getElementById("editor-image-wrap");
  const editorImageEl = document.getElementById("editor-image");
  const undoToolBtn = document.getElementById("undo-tool");
  const doneToolBtn = document.getElementById("done-tool");
  predictedImageEl = document.getElementById("prediction-image");
  predictedImageWrapEl = imageWrapEl;

  if (!stageEl || !imageWrapEl || !editorImageEl) {
    return;
  }

  activeStageEl = stageEl;
  activeImageWrapEl = imageWrapEl;

  const clickableCards = [...resultsEl.querySelectorAll(".image-card-button")];
  clickableCards.forEach((button) => {
    button.addEventListener("click", () => {
      const imageIndex = Number(button.dataset.imageIndex);
      const selected = rows[imageIndex];

      if (!selected) {
        return;
      }

      // Set the current image for prediction
      setCurrentImage(selected.imageName);

      editorImageEl.src = `images/${selected.imageName}`;
      stageEl.classList.add("is-editor-open");
      stageEl.classList.remove("is-prediction-done");

      const predOutput = document.getElementById("prediction-output");
      if (predOutput) {
        predOutput.classList.add("is-hidden");
        predOutput.innerHTML = "";
      }

      ensurePredictionElements();

      if (predictedImageEl) {
        predictedImageEl.src = "";
        predictedImageEl.classList.add("is-hidden");
      }

      // Clear any visible weather overlays
      const overlayDay0 = document.getElementById("weather-overlay-day0");
      const overlayDay3 = document.getElementById("weather-overlay-day3");
      if (overlayDay0) overlayDay0.classList.remove("is-weather-overlay-visible");
      if (overlayDay3) overlayDay3.classList.remove("is-weather-overlay-visible");
      currentWeatherDay = null;

      editorImageEl.onload = () => {
        initializeDrawingCanvas(imageWrapEl);
      };

      if (editorImageEl.complete) {
        initializeDrawingCanvas(imageWrapEl);
      }
    });
  });

  undoToolBtn.addEventListener("click", () => {
    undoLastStroke();
  });

  doneToolBtn.addEventListener("click", () => {
    const validation = validateDrawingShape();
    if (!validation.isValid) {
      setEditorError(validation.message);
      return;
    }

    setEditorError("");
    // Show the day 0 weather overlay
    const overlayDay0 = document.getElementById("weather-overlay-day0");
    if (overlayDay0) {
      overlayDay0.classList.add("is-weather-overlay-visible");
    }
  });

  setupWeatherControls(stageEl);

  if (!resizeHandlerAttached) {
    window.addEventListener("resize", () => {
      if (!activeStageEl || !activeImageWrapEl || !drawCanvas) {
        return;
      }

      if (!activeStageEl.classList.contains("is-editor-open")) {
        return;
      }

      initializeDrawingCanvas(activeImageWrapEl);
    });
    resizeHandlerAttached = true;
  }
}

function ensurePredictionElements() {
  if (!predictedImageEl) {
    predictedImageEl = document.getElementById("prediction-image");
  }
  if (!predictedImageWrapEl) {
    predictedImageWrapEl = document.getElementById("editor-image-wrap");
  }
}

function showPredictionResultView() {
  animateTitleSwap("predicted fire");
  if (activeStageEl) {
    activeStageEl.classList.add("is-prediction-done");
  }
}

function initializeDrawingCanvas(imageWrapEl) {
  drawCanvas = document.getElementById("draw-canvas");
  if (!drawCanvas) {
    return;
  }

  const pixelRatio = window.devicePixelRatio || 1;
  const rect = imageWrapEl.getBoundingClientRect();
  const cssWidth = Math.max(1, Math.floor(rect.width));
  const cssHeight = Math.max(1, Math.floor(rect.height));
  drawCanvas.width = Math.max(1, Math.floor(rect.width * pixelRatio));
  drawCanvas.height = Math.max(1, Math.floor(rect.height * pixelRatio));
  drawCanvas.style.width = `${cssWidth}px`;
  drawCanvas.style.height = `${cssHeight}px`;

  drawCtx = drawCanvas.getContext("2d");
  drawCtx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  drawCtx.clearRect(0, 0, cssWidth, cssHeight);

  snapshotStack = [drawCtx.getImageData(0, 0, cssWidth, cssHeight)];
  currentStrokePoints = [];
  completedStrokes = [];
  setEditorError("");
  setActiveTool("brush");

  drawCanvas.onpointerdown = startStroke;
  drawCanvas.onpointermove = moveStroke;
  drawCanvas.onpointerup = endStroke;
  drawCanvas.onpointerleave = endStroke;
}

function setActiveTool(toolName) {
  activeTool = toolName;

  if (drawCanvas) {
    drawCanvas.style.cursor = toolName === "brush" ? "crosshair" : "default";
  }
}

function startStroke(event) {
  if (activeTool !== "brush" || !drawCtx || !drawCanvas) {
    return;
  }

  isDrawing = true;
  drawCanvas.setPointerCapture(event.pointerId);
  lastPoint = pointerToCanvasPoint(event, drawCanvas);
  currentStrokePoints = [lastPoint];

  drawCtx.beginPath();
  drawCtx.moveTo(lastPoint.x, lastPoint.y);
}

function moveStroke(event) {
  if (!isDrawing || activeTool !== "brush" || !drawCtx || !drawCanvas) {
    return;
  }

  const point = pointerToCanvasPoint(event, drawCanvas);
  drawCtx.strokeStyle = "#e74734";
  drawCtx.lineWidth = 5;
  drawCtx.lineCap = "round";
  drawCtx.lineJoin = "round";
  drawCtx.lineTo(point.x, point.y);
  drawCtx.stroke();

  lastPoint = point;
  currentStrokePoints.push(point);
}

function endStroke(event) {
  if (!isDrawing || !drawCtx || !drawCanvas) {
    return;
  }

  isDrawing = false;
  if (drawCanvas.hasPointerCapture(event.pointerId)) {
    drawCanvas.releasePointerCapture(event.pointerId);
  }
  drawCtx.closePath();

  const rect = drawCanvas.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  snapshotStack.push(drawCtx.getImageData(0, 0, width, height));

  if (currentStrokePoints.length > 1) {
    completedStrokes.push(currentStrokePoints);
  }

  currentStrokePoints = [];
}

function undoLastStroke() {
  if (!drawCtx || snapshotStack.length <= 1 || !drawCanvas) {
    return;
  }

  snapshotStack.pop();
  const previous = snapshotStack[snapshotStack.length - 1];
  drawCtx.putImageData(previous, 0, 0);

  if (completedStrokes.length > 0) {
    completedStrokes.pop();
  }
}

function setupWeatherControls(stageEl) {
  const overlayDay0 = document.getElementById("weather-overlay-day0");
  const overlayDay3 = document.getElementById("weather-overlay-day3");
  const doneButtonDay0 = document.getElementById("weather-done-button-day0");
  const doneButtonDay3 = document.getElementById("weather-done-button-day3");

  // Setup sliders and direction controls for both days
  setupWeatherDay("day0");
  setupWeatherDay("day3");

  // Initialize: show day0, hide day3
  currentWeatherDay = 0;
  if (overlayDay0) overlayDay0.classList.add("is-weather-overlay-visible");
  if (overlayDay3) overlayDay3.classList.remove("is-weather-overlay-visible");

  // Day 0 done button: save day0 data and show day3
  if (doneButtonDay0) {
    doneButtonDay0.addEventListener("click", () => {
      saveWeatherDay("day0");
      console.log("Day 0 weather saved:", weatherData.day0);

      // Transition to day 3
      if (overlayDay0) overlayDay0.classList.remove("is-weather-overlay-visible");
      if (overlayDay3) overlayDay3.classList.add("is-weather-overlay-visible");
      currentWeatherDay = 3;
    });
  }

  // Day 3 done button: save day3 data and close
  if (doneButtonDay3) {
    doneButtonDay3.addEventListener("click", () => {
      saveWeatherDay("day3");
      console.log("Day 3 weather saved:", weatherData.day3);
      console.log("All weather data:", weatherData);

      // Close weather overlays
      if (overlayDay0) overlayDay0.classList.remove("is-weather-overlay-visible");
      if (overlayDay3) overlayDay3.classList.remove("is-weather-overlay-visible");
      currentWeatherDay = null;

      // Submit data to prediction API
      submitWeatherDataForPrediction();
    });
  }

  // Handle background overlay clicks to close
  if (overlayDay0) {
    overlayDay0.addEventListener("click", (event) => {
      if (event.target === overlayDay0) {
        overlayDay0.classList.remove("is-weather-overlay-visible");
        currentWeatherDay = null;
      }
    });
  }

  if (overlayDay3) {
    overlayDay3.addEventListener("click", (event) => {
      if (event.target === overlayDay3) {
        overlayDay3.classList.remove("is-weather-overlay-visible");
        currentWeatherDay = null;
      }
    });
  }
}

function setupWeatherDay(dayId) {
  const humidityInput = document.getElementById(`humidity-${dayId}-input`);
  const humidityValue = document.getElementById(`humidity-${dayId}-value`);
  const soilInput = document.getElementById(`soil-${dayId}-input`);
  const soilValue = document.getElementById(`soil-${dayId}-value`);
  const directionCircle = document.getElementById(`wind-direction-${dayId}-circle`);
  const directionLine = document.getElementById(`wind-direction-${dayId}-line`);
  const directionValue = document.getElementById(`wind-direction-${dayId}-value`);
  const directionInput = document.getElementById(`wind-direction-${dayId}-input`);

  if (!humidityInput || !humidityValue || !soilInput || !soilValue || !directionCircle || !directionLine || !directionValue || !directionInput) {
    return;
  }

  const updateSliderReadout = (inputEl, outputEl) => {
    outputEl.textContent = `${inputEl.value}%`;
  };

  updateSliderReadout(humidityInput, humidityValue);
  updateSliderReadout(soilInput, soilValue);

  humidityInput.addEventListener("input", () => {
    updateSliderReadout(humidityInput, humidityValue);
  });

  soilInput.addEventListener("input", () => {
    updateSliderReadout(soilInput, soilValue);
  });

  let dialDragging = false;

  const setWindDirection = (degrees) => {
    const normalized = ((Math.round(degrees) % 360) + 360) % 360;
    directionInput.value = String(normalized);
    directionValue.textContent = String(normalized);
    directionLine.style.transform = `translate(-50%, -100%) rotate(${normalized}deg)`;
    directionCircle.setAttribute("aria-valuenow", String(normalized));
  };

  const updateDirectionFromPointer = (event) => {
    const rect = directionCircle.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const dx = event.clientX - centerX;
    const dy = event.clientY - centerY;
    const degrees = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
    setWindDirection(degrees);
  };

  directionCircle.addEventListener("pointerdown", (event) => {
    dialDragging = true;
    directionCircle.setPointerCapture(event.pointerId);
    updateDirectionFromPointer(event);
  });

  directionCircle.addEventListener("pointermove", (event) => {
    if (!dialDragging) {
      return;
    }

    updateDirectionFromPointer(event);
  });

  directionCircle.addEventListener("pointerup", (event) => {
    if (!dialDragging) {
      return;
    }

    dialDragging = false;
    if (directionCircle.hasPointerCapture(event.pointerId)) {
      directionCircle.releasePointerCapture(event.pointerId);
    }
  });

  directionCircle.addEventListener("pointerleave", () => {
    dialDragging = false;
  });

  directionCircle.addEventListener("keydown", (event) => {
    const current = Number(directionInput.value);

    if (event.key === "ArrowRight" || event.key === "ArrowUp") {
      event.preventDefault();
      setWindDirection(current + 1);
    }

    if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
      event.preventDefault();
      setWindDirection(current - 1);
    }
  });

  setWindDirection(Number(directionInput.value));
}

function saveWeatherDay(dayId) {
  const key = dayId === "day0" ? "day0" : "day3";
  weatherData[key] = {
    temperature: parseFloat(document.getElementById(`temperature-${dayId}-input`).value) || null,
    humidity: parseFloat(document.getElementById(`humidity-${dayId}-input`).value) || null,
    precipitation: parseFloat(document.getElementById(`precip-${dayId}-input`).value) || null,
    soilMoisture: parseFloat(document.getElementById(`soil-${dayId}-input`).value) || null,
    windSpeed: parseFloat(document.getElementById(`wind-speed-${dayId}-input`).value) || null,
    windGust: parseFloat(document.getElementById(`wind-gust-${dayId}-input`).value) || null,
    windDirection: parseInt(document.getElementById(`wind-direction-${dayId}-input`).value) || null,
  };
}

function collectWeatherData() {
  const days = ["day0", "day3"];

  days.forEach((dayId) => {
    const key = dayId === "day0" ? "day0" : "day3";
    weatherData[key] = {
      temperature: parseFloat(document.getElementById(`temperature-${dayId}-input`).value) || null,
      humidity: parseFloat(document.getElementById(`humidity-${dayId}-input`).value) || null,
      precipitation: parseFloat(document.getElementById(`precip-${dayId}-input`).value) || null,
      soilMoisture: parseFloat(document.getElementById(`soil-${dayId}-input`).value) || null,
      windSpeed: parseFloat(document.getElementById(`wind-speed-${dayId}-input`).value) || null,
      windGust: parseFloat(document.getElementById(`wind-gust-${dayId}-input`).value) || null,
      windDirection: parseInt(document.getElementById(`wind-direction-${dayId}-input`).value) || null,
    };
  });
}

function validateDrawingShape() {
  const closedStrokes = completedStrokes.filter((stroke) => isStrokeClosed(stroke));

  if (closedStrokes.length === 0) {
    return {
      isValid: false,
      message: "Error: shape must be enclosed.",
    };
  }

  return { isValid: true, message: "" };
}

function getFireMaskDataUrl() {
  if (!drawCanvas || completedStrokes.length === 0) {
    return null;
  }

  const closedStrokes = completedStrokes.filter((stroke) => isStrokeClosed(stroke));
  if (closedStrokes.length === 0) {
    return null;
  }

  const rect = drawCanvas.getBoundingClientRect();
  const maskCanvas = document.createElement("canvas");
  maskCanvas.width = Math.max(1, Math.floor(rect.width));
  maskCanvas.height = Math.max(1, Math.floor(rect.height));

  const ctx = maskCanvas.getContext("2d");
  ctx.fillStyle = "black";
  ctx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);

  ctx.fillStyle = "white";
  closedStrokes.forEach((stroke) => {
    ctx.beginPath();
    stroke.forEach((point, index) => {
      if (index === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    ctx.closePath();
    ctx.fill();
  });

  return maskCanvas.toDataURL("image/png");
}

function showPredictionImage(dataUrl) {
  if (!predictedImageEl || !predictedImageWrapEl) {
    ensurePredictionElements();
  }

  if (!predictedImageEl || !predictedImageWrapEl) {
    return;
  }
  predictedImageEl.src = dataUrl;
  predictedImageEl.classList.remove("is-hidden");
}

function isStrokeClosed(stroke) {
  if (!drawCanvas || !stroke || stroke.length < 4) {
    return false;
  }

  const first = stroke[0];
  const last = stroke[stroke.length - 1];
  const dx = first.x - last.x;
  const dy = first.y - last.y;
  const closeDistance = Math.sqrt(dx * dx + dy * dy);
  const rect = drawCanvas.getBoundingClientRect();
  const closureThreshold = Math.max(10, Math.min(rect.width, rect.height) * 0.045);

  return closeDistance <= closureThreshold;
}


function setEditorError(message) {
  const editorErrorEl = document.getElementById("editor-error");
  if (!editorErrorEl) {
    return;
  }

  editorErrorEl.textContent = message;
}

function pointerToCanvasPoint(event, canvasEl) {
  const rect = canvasEl.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function shuffle(items) {
  const clone = [...items];

  for (let i = clone.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [clone[i], clone[j]] = [clone[j], clone[i]];
  }

  return clone;
}
