/* ================================================
   app.js — CropSense AI Dashboard Logic
   AI-Driven IoT Crop Monitoring System
   ================================================ */

// ── Configuration ──────────────────────────────
// Auto-detect backend: if served by Flask use same origin, else fallback to localhost:5000
const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? `${window.location.protocol}//${window.location.hostname}:5000`
  : "http://localhost:5000";
const AUTO_REFRESH_MS = 30000;             // Auto-refresh sensor data every 30s

// ── State ──────────────────────────────────────
let latestSensorData = null;
let autoRefreshTimer = null;


// ═══════════════════════════════════════════════
//  SENSOR DATA
// ═══════════════════════════════════════════════

/**
 * Fetch sensor data from Flask backend and update the UI cards.
 */
async function fetchSensorData() {
  const refreshBtn = document.getElementById("refreshBtn");
  refreshBtn.classList.add("spinning");

  try {
    const res = await fetch(`${API_BASE}/api/sensor-data`);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    latestSensorData = data;

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
 * Update all three sensor cards with the fetched data.
 */
function updateSensorCards(data) {
  // ── Soil Moisture ──
  const moisture = data.soil_moisture;
  document.getElementById("soilMoisture").textContent = moisture.toFixed(1);
  document.getElementById("moistureBar").style.width  = `${Math.min(moisture, 100)}%`;
  setMoistureColor(moisture);

  const moistureStatus = document.getElementById("moistureStatus");
  moistureStatus.textContent = data.moisture_status || "";
  setStatusStyle(moistureStatus, data.moisture_status);

  // ── Temperature ──
  const temp = data.temperature;
  document.getElementById("temperature").textContent = temp.toFixed(1);
  document.getElementById("tempBar").style.width = `${Math.min((temp / 50) * 100, 100)}%`;

  const tempStatus = document.getElementById("tempStatus");
  tempStatus.textContent = data.temp_status || "";
  setStatusStyle(tempStatus, data.temp_status);

  // Set progress bar color for temp
  const tempBar = document.getElementById("tempBar");
  if (temp > 35)      tempBar.style.background = "var(--accent-danger)";
  else if (temp < 22) tempBar.style.background = "var(--accent-blue)";
  else                tempBar.style.background = "var(--accent)";

  // ── Humidity ──
  const humidity = data.humidity;
  document.getElementById("humidity").textContent  = humidity.toFixed(1);
  document.getElementById("humidityBar").style.width = `${Math.min(humidity, 100)}%`;

  const humidityBar = document.getElementById("humidityBar");
  if (humidity > 85)      humidityBar.style.background = "var(--accent-warn)";
  else if (humidity < 40) humidityBar.style.background = "var(--accent-danger)";
  else                    humidityBar.style.background = "var(--accent-blue)";

  // ── Metadata ──
  document.getElementById("lastUpdated").textContent = data.timestamp_human || new Date().toLocaleString();

  const sourceEl = document.getElementById("dataSource");
  sourceEl.textContent = data.source || "dummy";
  sourceEl.style.color = data.source === "esp32" ? "var(--accent)" : "var(--accent-blue)";
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
 * Apply warning/danger/ok style to a status badge element.
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


// ═══════════════════════════════════════════════
//  CHATBOT
// ═══════════════════════════════════════════════

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

  // Display user message
  appendMessage("user", query);
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  sendBtn.innerHTML = "⏳";

  // Show typing indicator
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
      appendMessage("bot", `⚠️ Error ${res.status}: ${errData.error || "Unknown error"}`);
      return;
    }

    const data = await res.json();
    appendMessage("bot", data.response);

    // Update sensor cards if fresh data returned
    if (data.sensor_context) {
      latestSensorData = data.sensor_context;
      updateSensorCards(data.sensor_context);
    }

  } catch (err) {
    removeTypingIndicator(typingId);
    appendMessage("bot", "⚠️ Could not reach the backend. Make sure Flask is running on port 5000.");
    console.error("Chat error:", err);
  } finally {
    input.disabled  = false;
    sendBtn.disabled = false;
    sendBtn.innerHTML = "➤";
    input.focus();
  }
}


/**
 * Append a chat bubble to the message list.
 * @param {string} role  - "user" or "bot"
 * @param {string} text  - Message content (supports newlines)
 */
function appendMessage(role, text) {
  const container = document.getElementById("chatMessages");

  const wrapper = document.createElement("div");
  wrapper.className = `chat-message ${role === "user" ? "user-message" : "bot-message"}`;

  const avatar = document.createElement("span");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "👨‍🌾" : "🌿";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";

  // Convert newlines to <br> and preserve formatting
  bubble.innerHTML = escapeHTML(text).replace(/\n/g, "<br>");

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);

  // Auto-scroll to latest message
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
  avatar.textContent = "🌿";

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
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}


// ═══════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════

/**
 * Initialize the dashboard on page load.
 */
function init() {
  // Fetch sensor data immediately
  fetchSensorData();

  // Auto-refresh every 30 seconds
  autoRefreshTimer = setInterval(fetchSensorData, AUTO_REFRESH_MS);

  console.log("🌾 CropSense AI Dashboard initialized");
  console.log(`   Backend: ${API_BASE}`);
  console.log(`   Auto-refresh: every ${AUTO_REFRESH_MS / 1000}s`);
}

// Start on DOM ready
document.addEventListener("DOMContentLoaded", init);
