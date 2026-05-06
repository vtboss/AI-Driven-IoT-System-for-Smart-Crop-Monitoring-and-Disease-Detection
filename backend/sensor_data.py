"""
==========================================================
 sensor_data.py — Sensor Reading Module
==========================================================
 Phase 1: Returns DUMMY/SIMULATED sensor values.
 Phase 2: Will be replaced with real ESP32 data via POST.

 Sensors simulated:
   - Soil Moisture Sensor (analog → percentage)
   - DHT22 (Temperature in °C, Humidity in %)
==========================================================
"""

import random
import time


# ──────────────────────────────────────────────
# In-memory store for latest sensor readings.
# When ESP32 is connected, it will POST here
# and update this dictionary.
# ──────────────────────────────────────────────
_latest_sensor_data = {
    "soil_moisture": 45.0,    # %
    "temperature": 28.0,      # °C
    "humidity": 65.0,         # %
    "timestamp": time.time(),
    "source": "dummy"         # Will change to "esp32" later
}


def get_sensor_data() -> dict:
    """
    Returns the latest sensor readings.

    Currently SIMULATES realistic sensor fluctuations
    so the frontend and chatbot have dynamic data to work with.

    Soil Moisture: 20–80% (realistic field range)
    Temperature  : 22–38°C (tropical/subtropical crops)
    Humidity     : 40–95%  (varies by weather)
    """
    # Simulate small realistic fluctuations each call
    soil_moisture = round(random.uniform(20.0, 80.0), 1)
    temperature   = round(random.uniform(22.0, 38.0), 1)
    humidity      = round(random.uniform(40.0, 95.0), 1)

    # Derive a simple status label based on moisture level
    if soil_moisture < 30:
        moisture_status = "Dry — Irrigation Needed"
    elif soil_moisture < 60:
        moisture_status = "Optimal"
    else:
        moisture_status = "Wet — Reduce Watering"

    # Derive heat stress indicator
    if temperature > 35:
        temp_status = "Heat Stress Risk"
    elif temperature < 25:
        temp_status = "Cool — Monitor for Disease"
    else:
        temp_status = "Optimal"

    data = {
        "soil_moisture":    soil_moisture,
        "temperature":      temperature,
        "humidity":         humidity,
        "moisture_status":  moisture_status,
        "temp_status":      temp_status,
        "timestamp":        time.time(),
        "timestamp_human":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "source":           "dummy"   # Change to "esp32" when hardware connected
    }

    # Update in-memory store
    global _latest_sensor_data
    _latest_sensor_data = data

    return data


def update_sensor_data(soil_moisture: float, temperature: float, humidity: float):
    """
    Called when ESP32 POSTs real sensor data.
    Replaces dummy values with actual hardware readings.
    (Will be used in Phase 2 — ESP32 integration)
    """
    global _latest_sensor_data
    _latest_sensor_data = {
        "soil_moisture":   round(soil_moisture, 1),
        "temperature":     round(temperature, 1),
        "humidity":        round(humidity, 1),
        "timestamp":       time.time(),
        "timestamp_human": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source":          "esp32"
    }
    return _latest_sensor_data
