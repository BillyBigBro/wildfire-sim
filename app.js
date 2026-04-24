const titleEl = document.getElementById("page-title");
const selectEl = document.getElementById("state-select");
const resultsEl = document.getElementById("results");

const STATES = [
  "Arizona",
  "California",
  "Colorado",
  "Florida",
  "Georgia",
  "Idaho",
  "Kansas",
  "Montana",
  "Nevada",
  "New Mexico",
  "Oregon",
  "Texas",
  "Utah",
  "Washington",
  "Wyoming",
];

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

let imagesData = [];
let stateFeatures = [];

const dataReady = Promise.all([
  fetch("coordinates.csv").then((response) => response.text()),
  fetch("https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json").then((response) =>
    response.json(),
  ),
])
  .then(([csvText, geoJson]) => {
    stateFeatures = geoJson.features.filter((feature) => STATES.includes(feature.properties.name));
    imagesData = parseCsv(csvText);
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
        <p class="editor-subtitle">(shape must encompass the square)</p>
        <div class="editor-image-wrap" id="editor-image-wrap">
          <img id="editor-image" src="" alt="Selected satellite image" />
          <canvas id="draw-canvas"></canvas>
          <span class="target-square" aria-hidden="true"></span>
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

        <section class="weather-overlay" id="weather-overlay" aria-label="Input weather conditions">
          <div class="weather-panel">
            <h3>input weather conditions:</h3>
            <div class="weather-grid">
              <div class="weather-col">
                <label for="temperature-input">temperature (C)</label>
                <input id="temperature-input" type="number" step="0.1" />

                <label for="humidity-input">relative humidity (%)</label>
                <div class="slider-field">
                  <input id="humidity-input" type="range" min="0" max="100" value="50" />
                  <span id="humidity-value">50%</span>
                </div>

                <label for="precip-input">precipitation (mm)</label>
                <input id="precip-input" type="number" step="0.1" min="0" />

                <label for="soil-input">soil moisture (%)</label>
                <div class="slider-field">
                  <input id="soil-input" type="range" min="0" max="100" value="50" />
                  <span id="soil-value">50%</span>
                </div>
              </div>

              <div class="weather-col">
                <label for="wind-speed-input">wind speed (km/h)</label>
                <input id="wind-speed-input" type="number" step="0.1" min="0" />

                <label for="wind-gust-input">wind gust speed (km/h)</label>
                <input id="wind-gust-input" type="number" step="0.1" min="0" />

                <label for="wind-direction-input">wind direction (deg.)</label>
                <div class="wind-direction-picker">
                  <div id="wind-direction-circle" class="wind-direction-circle" role="slider" aria-label="Wind direction" aria-valuemin="0" aria-valuemax="359" aria-valuenow="0" tabindex="0">
                    <div id="wind-direction-line" class="wind-direction-line"></div>
                    <span class="wind-direction-dot" aria-hidden="true"></span>
                  </div>
                  <span class="wind-direction-readout"><span id="wind-direction-value">0</span>deg</span>
                  <input id="wind-direction-input" type="hidden" value="0" />
                </div>
              </div>
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

      editorImageEl.src = `images/${selected.imageName}`;
      stageEl.classList.add("is-editor-open");
      stageEl.classList.remove("is-weather-open");

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
    stageEl.classList.add("is-weather-open");
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
  const humidityInput = document.getElementById("humidity-input");
  const humidityValue = document.getElementById("humidity-value");
  const soilInput = document.getElementById("soil-input");
  const soilValue = document.getElementById("soil-value");
  const directionCircle = document.getElementById("wind-direction-circle");
  const directionLine = document.getElementById("wind-direction-line");
  const directionValue = document.getElementById("wind-direction-value");
  const directionInput = document.getElementById("wind-direction-input");
  const weatherOverlay = document.getElementById("weather-overlay");

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

  if (weatherOverlay) {
    weatherOverlay.addEventListener("click", (event) => {
      if (event.target === weatherOverlay) {
        stageEl.classList.remove("is-weather-open");
      }
    });
  }

  setWindDirection(Number(directionInput.value));
}

function validateDrawingShape() {
  const closedStrokes = completedStrokes.filter((stroke) => isStrokeClosed(stroke));

  if (closedStrokes.length === 0) {
    return {
      isValid: false,
      message: "Error: shape must be enclosed.",
    };
  }

  const centerPoint = getCanvasCenterPoint();
  const containsCenter = closedStrokes.some((stroke) => isPointInsideStrokePolygon(centerPoint, stroke));

  if (!containsCenter) {
    return {
      isValid: false,
      message: "Error: shape must encapsulate the red square.",
    };
  }

  return { isValid: true, message: "" };
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

function getCanvasCenterPoint() {
  const rect = drawCanvas ? drawCanvas.getBoundingClientRect() : { width: 0, height: 0 };
  return {
    x: rect.width / 2,
    y: rect.height / 2,
  };
}

function isPointInsideStrokePolygon(point, stroke) {
  let inside = false;

  for (let i = 0, j = stroke.length - 1; i < stroke.length; j = i, i += 1) {
    const xi = stroke[i].x;
    const yi = stroke[i].y;
    const xj = stroke[j].x;
    const yj = stroke[j].y;

    const intersects = yi > point.y !== yj > point.y && point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
    if (intersects) {
      inside = !inside;
    }
  }

  return inside;
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
