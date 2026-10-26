"""
==============================================================
 app.py  --  Flask Backend
 AI-Driven IoT Crop Monitoring System
==============================================================
 Phase 2  |  ESP32 -> SQLite -> Dashboard
----------------------------------------------------------
 Routes:
   GET  /                    Health check
   GET  /dashboard           Serve dashboard HTML
   GET  /dashboard/<file>    Serve dashboard assets
   GET  /api/sensor-data     Return latest reading from DB
   POST /api/sensor-data     Receive ESP32 JSON, store in DB
   GET  /api/history         Return last N readings for charts
   POST /api/chat            AI advisory with sensor context
 Run:  python app.py
 URL:  http://localhost:5000
==============================================================
"""
import sys
import io
# Fix emoji printing on Windows terminals (cp1252 -> utf-8)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from flask import Flask, jsonify, request, send_from_directory
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load .env from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from database    import init_db, get_history as db_get_history
from sensor_data import get_sensor_data, update_sensor_data
from chatbot     import get_chatbot_response


# ── App Initialization ──────────────────────────────────────────────────────
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")
CORS(app)   # Allow any origin (dashboard served via Flask, ESP32 from same LAN)

# Create sensor_data.db + table if they do not exist
init_db()


# ── Route: Serve Dashboard ──────────────────────────────────────────────────
@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Serve the main dashboard HTML page."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/dashboard/<path:filename>", methods=["GET"])
def dashboard_assets(filename):
    """Serve CSS / JS / assets for the dashboard."""
    return send_from_directory(FRONTEND_DIR, filename)


# ── Route: Favicon ─────────────────────────────────────────────────────────
@app.route("/favicon.ico", methods=["GET"])
def favicon():
    """Return an SVG favicon so browsers stop logging 404."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">&#127807;</text></svg>'
    return app.response_class(svg, mimetype="image/svg+xml")


# ── Route: Health Check ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    """Simple health check -- confirms server is running."""
    return jsonify({
        "status":    "online",
        "message":   "Crop Monitoring Backend is running",
        "version":   "2.0.0",
        "dashboard": "http://localhost:5000/dashboard"
    })


# ── Route: GET /api/sensor-data ─────────────────────────────────────────────
@app.route("/api/sensor-data", methods=["GET"])
def get_sensor():
    """
    Return the latest sensor reading from SQLite.

    Response (200):
        {
            "id": 42,
            "temperature": 28.6,
            "humidity": 71.2,
            "soil_moisture": 1834,       <- raw ADC
            "soil_moisture_pct": 68.3,   <- 0-100 % for UI
            "rain": 1,
            "moisture_status": "Optimal",
            "temp_status": "Optimal",
            "timestamp": "2026-08-21 11:30:00",
            "source": "esp32"
        }

    If no readings exist yet:
        { "error": "no_data", "message": "...", "source": "none" }
    """
    data = get_sensor_data()
    return jsonify(data), 200


# ── Route: POST /api/sensor-data ────────────────────────────────────────────
@app.route("/api/sensor-data", methods=["POST"])
def post_sensor():
    """
    Receive a JSON payload from the ESP32 and store it in SQLite.

    Expected payload:
        {
            "temperature":   28.6,
            "humidity":      71.2,
            "soil_moisture": 1834,
            "rain":          0
        }

    rain field is accepted and stored but not displayed on the dashboard.

    Returns 201 with the stored + enriched reading on success.
    Returns 400 on missing/invalid fields.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Validate required fields
    required = ["temperature", "humidity", "soil_moisture"]
    missing  = [f for f in required if f not in body]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    # Parse and type-check
    try:
        temperature   = float(body["temperature"])
        humidity      = float(body["humidity"])
        soil_moisture = int(body["soil_moisture"])
        rain          = int(body.get("rain", 1))    # default: no rain
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid data types: {exc}"}), 400

    # Basic range sanity checks
    if not (-10 <= temperature <= 60):
        return jsonify({"error": "temperature out of range (-10 to 60 C)"}), 400
    if not (0 <= humidity <= 100):
        return jsonify({"error": "humidity out of range (0-100)"}), 400
    if not (0 <= soil_moisture <= 4095):
        return jsonify({"error": "soil_moisture out of range (0-4095)"}), 400

    stored = update_sensor_data(temperature, humidity, soil_moisture, rain)
    return jsonify(stored), 201


# ── Route: GET /api/history ─────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def history():
    """
    Return recent sensor readings for dashboard charts.

    Query parameters:
        limit  (int, optional) -- number of readings to return, default 50, max 200

    Response (200):
        [
            { "id": 42, "temperature": ..., "timestamp": ... },
            ...
        ]
    """
    try:
        limit = int(request.args.get("limit", 50))
        limit = max(1, min(limit, 200))
    except (ValueError, TypeError):
        limit = 50

    rows = db_get_history(limit)
    return jsonify(rows), 200


# ── Route: POST /api/chat ───────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Receive a user query from the frontend.
    Combine it with the latest sensor data as context.
    Return AI-generated agricultural advice.

    Request body (JSON):
        { "query": "Should I water my tomato plants?" }

    Response (JSON):
        { "response": "...", "sensor_context": {...} }
    """
    body = request.get_json()
    if not body or "query" not in body:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_query = body["query"].strip()
    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    sensor      = get_sensor_data()
    ai_response = get_chatbot_response(user_query, sensor)

    return jsonify({
        "response":       ai_response,
        "sensor_context": sensor
    })


# ── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    print("=" * 58)
    print(" [*] AI Crop Monitoring -- Backend Starting (v2.0)...")
    print("=" * 58)
    print(f" Health Check  : http://localhost:{port}/")
    print(f" Sensor (GET)  : http://localhost:{port}/api/sensor-data")
    print(f" Sensor (POST) : http://localhost:{port}/api/sensor-data  <- ESP32")
    print(f" History       : http://localhost:{port}/api/history")
    print(f" Chatbot       : http://localhost:{port}/api/chat  [POST]")
    print(f" Dashboard     : http://localhost:{port}/dashboard")
    print("=" * 58)
    app.run(debug=debug, host="0.0.0.0", port=port, threaded=True)


