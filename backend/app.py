"""
==========================================================
 AI-Driven IoT Crop Monitoring System — Flask Backend
==========================================================
 Phase 1 | Step 1: Flask backend with dummy sensor data
 Step 2:          API endpoint for sensor data
 Step 3:          Chatbot (NVIDIA API) integration
----------------------------------------------------------
 Run:  python app.py
 URL:  http://localhost:5000
==========================================================
"""
import sys
import io
# Fix emoji printing on Windows terminals (cp1252 -> utf-8)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from flask import Flask, jsonify, request, send_from_directory
import os
from dotenv import load_dotenv
from flask_cors import CORS
import random
import time

# Load .env from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sensor_data import get_sensor_data
from chatbot import get_chatbot_response

# ──────────────────────────────────────────────
# App Initialization
# ──────────────────────────────────────────────
# Resolve frontend folder (one level up from backend/)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")
CORS(app)  # Allow frontend (any origin) to talk to this backend


# ──────────────────────────────────────────────
# Route: Serve Dashboard Frontend
# ──────────────────────────────────────────────
@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Serve the main dashboard HTML page."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/dashboard/<path:filename>", methods=["GET"])
def dashboard_assets(filename):
    """Serve CSS/JS/assets for the dashboard."""
    return send_from_directory(FRONTEND_DIR, filename)


# ──────────────────────────────────────────────
# Route: Health Check (API only)
# ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    """Simple health check — confirms server is running."""
    return jsonify({
        "status": "online",
        "message": "Crop Monitoring Backend is running",
        "version": "1.0.0",
        "dashboard": "http://localhost:5000/dashboard"
    })


# ──────────────────────────────────────────────
# Route: GET /api/sensor-data
# Returns latest sensor readings (dummy for now)
# ──────────────────────────────────────────────
@app.route("/api/sensor-data", methods=["GET"])
def sensor_data():
    """
    Returns the latest sensor readings.
    Currently uses dummy/simulated data.
    Later: will receive real data from ESP32.
    """
    data = get_sensor_data()
    return jsonify(data)


# ──────────────────────────────────────────────
# Route: POST /api/chat
# Accepts user query + sensor context → AI response
# ──────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Receives a user query from the frontend.
    Combines it with latest sensor data.
    Returns AI-generated agricultural advice.
    
    Request body (JSON):
        { "query": "Why are my leaves yellowing?" }
    
    Response (JSON):
        { "response": "...", "sensor_context": {...} }
    """
    body = request.get_json()

    # Validate request
    if not body or "query" not in body:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_query = body["query"].strip()
    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # Get current sensor readings to build context
    sensor = get_sensor_data()

    # Get AI response
    ai_response = get_chatbot_response(user_query, sensor)

    return jsonify({
        "response": ai_response,
        "sensor_context": sensor  # Echo back what sensor data was used
    })


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    print("=" * 55)
    print(" [*] AI Crop Monitoring -- Backend Starting...")
    print("=" * 55)
    print(f" Health Check : http://localhost:{port}/")
    print(f" Sensor Data  : http://localhost:{port}/api/sensor-data")
    print(f" Chatbot      : http://localhost:{port}/api/chat  [POST]")
    print(f" Dashboard    : http://localhost:{port}/dashboard")
    print("=" * 55)
    app.run(debug=debug, host="0.0.0.0", port=port)
