/* ================================================
   app.js  --  CropSense AI Dashboard Logic
   AI-Driven IoT Crop Monitoring System
   Phase 2: Connected to SQLite via Flask
   ================================================ */

// ── Configuration ─────────────────────────────────────────────────────────
// Auto-detect backend: same origin when served by Flask, else localhost:5000
const API_BASE = (
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
)
  ? `${window.location.protocol}//${window.location.hostname}:5000`
  : "http://localhost:5000";

const AUTO_REFRESH_MS = 30000;   // Auto-refresh sensor data every 30 s

// ── State ─────────────────────────────────────────────────────────────────
let latestSensorData = null;
let autoRefreshTimer = null;


// ════════════════════════════════════════════════════════════════════════════
//  SENSOR DATA
// ════════════════════════════════════════════════════════════════════════════

/**
 * Fetch the latest sensor reading from Flask and update the UI cards.
 * Handles three states:
 *   1. Success with ESP32 data  -> update cards normally
 *   2. no_data sentinel         -> show "Waiting for ESP32..." placeholder
 *   3. Network / server error   -> mark connection offline
 */
async function fetchSensorData() {
  const refreshBtn = document.getElementById("refreshBtn");
  refreshBtn.classList.add("spinning");

  try {
    const res = await fetch(`${API_BASE}/api/sensor-data`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    latestSensorData = data;

    // Handle "no readings yet" sentinel from backend
    if (data.error === "no_data") {
      showNoDataPlaceholder();
      setConnectionStatus(true);   // Backend is online, just no ESP32 data yet
      return;
    }

    updateSensorCards(data);
    setConnectionStatus(true);

  } catch (err) {
    console.error("Sensor fetch error:", err);
    setConnectionStatus(false);
  } finally {
    refreshBtn.classList.remove("spinning");
  }
}


/**
 * Show placeholder text in all sensor cards when no ESP32 data exists yet.
 */
function showNoDataPlaceholder() {
  const waiting = "...";
  ["soilMoisture", "temperature", "humidity"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = waiting;
  });
  ["moistureBar", "tempBar", "humidityBar"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.width = "0%";
  });

  const moistureStatus = document.getElementById("moistureStatus");
  const tempStatus     = document.getElementById("tempStatus");
  if (moistureStatus) moistureStatus.textContent = "Waiting for ESP32...";
  if (tempStatus)     tempStatus.textContent     = "Waiting for ESP32...";

  const lastUpdated = document.getElementById("lastUpdated");
  if (lastUpdated) lastUpdated.textContent = "No data yet";

  const sourceEl = document.getElementById("dataSource");
  if (sourceEl) {
    sourceEl.textContent  = "none";
    sourceEl.style.color  = "var(--text-dim)";
  }
}


/**
 * Update all three sensor cards with a live reading from the backend.
 *
 * Uses soil_moisture_pct (0-100 %) for the progress bar and display.
 * Falls back to raw soil_moisture if pct is absent (backward-compatible).
 */
function updateSensorCards(data) {
  // ── Soil Moisture ────────────────────────────────────────────────────────
  // soil_moisture_pct is the ADC-converted percentage (0-100)
  const moisture = (data.soil_moisture_pct !== undefined)
    ? data.soil_moisture_pct
    : data.soil_moisture;

  document.getElementById("soilMoisture").textContent = moisture.toFixed(1);
  document.getElementById("moistureBar").style.width  = `${Math.min(moisture, 100)}%`;
  setMoistureColor(moisture);

  const moistureStatus = document.getElementById("moistureStatus");
  moistureStatus.textContent = data.moisture_status || "";
  setStatusStyle(moistureStatus, data.moisture_status);

  // ── Temperature ──────────────────────────────────────────────────────────
  const temp = data.temperature;
  document.getElementById("temperature").textContent = temp.toFixed(1);
  document.getElementById("tempBar").style.width = `${Math.min((temp / 50) * 100, 100)}%`;

  const tempStatus = document.getElementById("tempStatus");
  tempStatus.textContent = data.temp_status || "";
  setStatusStyle(tempStatus, data.temp_status);

  const tempBar = document.getElementById("tempBar");
  if (temp > 35)      tempBar.style.background = "var(--accent-danger)";
  else if (temp < 22) tempBar.style.background = "var(--accent-blue)";
  else                tempBar.style.background = "var(--accent)";

  // ── Humidity ─────────────────────────────────────────────────────────────
  const humidity = data.humidity;
  document.getElementById("humidity").textContent  = humidity.toFixed(1);
  document.getElementById("humidityBar").style.width = `${Math.min(humidity, 100)}%`;

  const humidityBar = document.getElementById("humidityBar");
  if (humidity > 85)      humidityBar.style.background = "var(--accent-warn)";
  else if (humidity < 40) humidityBar.style.background = "var(--accent-danger)";
  else                    humidityBar.style.background = "var(--accent-blue)";

  // ── Metadata ─────────────────────────────────────────────────────────────
  document.getElementById("lastUpdated").textContent =
    data.timestamp_human || new Date().toLocaleString();

  const sourceEl = document.getElementById("dataSource");
  sourceEl.textContent = data.source || "unknown";
  sourceEl.style.color = data.source === "esp32"
    ? "var(--accent)"
    : "var(--accent-blue)";
}


/**
 * Fetch the last N readings for charting.
 * Scaffolded and ready -- wire to Chart.js when charts are added.
 *
 * @param {number} limit - Number of readings to fetch (default 50)
 * @returns {Array}  Array of reading objects, newest first
 */
async function fetchHistory(limit = 50) {
  try {
    const res = await fetch(`${API_BASE}/api/history?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log(`[History] Fetched ${data.length} readings`);
    return data;
  } catch (err) {
    console.error("History fetch error:", err);
    return [];
  }
}


/**
 * Set moisture progress bar color based on level.
 */
function setMoistureColor(value) {
  const bar = document.getElementById("moistureBar");
  if (value < 30)      bar.style.background = "var(--accent-danger)";
  else if (value > 70) bar.style.background = "var(--accent-warn)";
  else                 bar.style.background = "var(--accent)";
}


/**
 * Apply warning / danger / ok style to a status badge element.
 */
function setStatusStyle(el, statusText) {
  el.classList.remove("warn", "danger");
  if (!statusText) return;
  const lower = statusText.toLowerCase();
  if (lower.includes("needed") || lower.includes("stress") || lower.includes("danger")) {
    el.classList.add("danger");
  } else if (lower.includes("wet") || lower.includes("disease") || lower.includes("heat")) {
    el.classList.add("warn");
  }
}


/**
 * Update the connection status badge in the header.
 */
function setConnectionStatus(online) {
  const badge = document.getElementById("connectionStatus");
  const text  = document.getElementById("statusText");
  badge.classList.remove("online", "offline");
  if (online) {
    badge.classList.add("online");
    text.textContent = "Connected";
  } else {
    badge.classList.add("offline");
    text.textContent = "Backend Offline";
  }
}


// ════════════════════════════════════════════════════════════════════════════
//  CHATBOT
// ════════════════════════════════════════════════════════════════════════════

/**
 * Handle Enter key in the textarea (send on Enter, newline on Shift+Enter).
 */
function handleEnter(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendQuery();
  }
}


/**
 * Pre-fill the query input with a quick-prompt suggestion.
 */
function setQuery(text) {
  const input = document.getElementById("userQuery");
  input.value = text;
  input.focus();
}


/**
 * Send user query to backend chatbot endpoint.
 * Displays the user message, a typing indicator, then the AI response.
 */
async function sendQuery() {
  const input   = document.getElementById("userQuery");
  const sendBtn = document.getElementById("sendBtn");
  const query   = input.value.trim();

  if (!query) return;

  appendMessage("user", query);
  input.value      = "";
  input.disabled   = true;
  sendBtn.disabled = true;
  sendBtn.innerHTML = "&#9201;";   // hourglass icon while waiting

  const typingId = showTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query })
    });

    removeTypingIndicator(typingId);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      appendMessage("bot", `[!] Error ${res.status}: ${errData.error || "Unknown error"}`);
      return;
    }

    const data = await res.json();
    appendMessage("bot", data.response);

    // Update sensor cards with fresh context returned by the AI route
    if (data.sensor_context && !data.sensor_context.error) {
      latestSensorData = data.sensor_context;
      updateSensorCards(data.sensor_context);
    }

  } catch (err) {
    removeTypingIndicator(typingId);
    appendMessage("bot", "[!] Could not reach the backend. Make sure Flask is running on port 5000.");
    console.error("Chat error:", err);
  } finally {
    input.disabled   = false;
    sendBtn.disabled = false;
    sendBtn.innerHTML = "&#11104;";  // send icon
    input.focus();
  }
}


/**
 * Append a chat bubble to the message list.
 * @param {string} role - "user" or "bot"
 * @param {string} text - Message content (supports newlines)
 */
function appendMessage(role, text) {
  const container = document.getElementById("chatMessages");

  const wrapper = document.createElement("div");
  wrapper.className = `chat-message ${role === "user" ? "user-message" : "bot-message"}`;

  const avatar = document.createElement("span");
  avatar.className = "msg-avatar";
  avatar.innerHTML = role === "user" ? "&#128100;" : "&#129302;";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = escapeHTML(text).replace(/\n/g, "<br>");

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}


/**
 * Show a "typing..." animation while waiting for the AI response.
 * @returns {string} ID of the typing element (for removal)
 */
function showTypingIndicator() {
  const container = document.getElementById("chatMessages");
  const id = `typing-${Date.now()}`;

  const wrapper = document.createElement("div");
  wrapper.className = "chat-message bot-message typing-indicator";
  wrapper.id = id;

  const avatar = document.createElement("span");
  avatar.className = "msg-avatar";
  avatar.innerHTML = "&#129302;";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = `
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
  `;

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;

  return id;
}


/**
 * Remove the typing indicator by its ID.
 */
function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}


/**
 * Escape HTML special characters to prevent XSS.
 */
function escapeHTML(str) {
  return str
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;");
}


// ════════════════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════════════════

/**
 * Initialize the dashboard on page load.
 */
function init() {
  fetchSensorData();
  autoRefreshTimer = setInterval(fetchSensorData, AUTO_REFRESH_MS);

  console.log("CropSense AI Dashboard initialized (Phase 2 -- SQLite)");
  console.log(`   Backend      : ${API_BASE}`);
  console.log(`   Auto-refresh : every ${AUTO_REFRESH_MS / 1000}s`);
}

// Start on DOM ready
document.addEventListener("DOMContentLoaded", init);

