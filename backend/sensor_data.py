"""
==============================================================
 sensor_data.py  --  Sensor Reading Module  (Phase 2: SQLite)
 AI-Driven IoT Crop Monitoring System
==============================================================
 Phase 1: Returned random dummy values.
 Phase 2: Reads from / writes to SQLite via database.py.

 Capacitive Soil Moisture Calibration:
   SOIL_DRY_ADC = 3200  (sensor in open air)
   SOIL_WET_ADC = 1200  (sensor submerged in water)
   Percentage  = (DRY - raw) / (DRY - WET) * 100  clamped 0-100
==============================================================
"""

from database import insert_reading, get_latest_reading


# ── Capacitive Sensor Calibration ─────────────────────────────────────────
# Adjust these two values if your sensor reads differently:
SOIL_DRY_ADC = 3200   # ADC value when sensor is in open air (0 % moisture)
SOIL_WET_ADC = 1200   # ADC value when sensor is submerged  (100 % moisture)


# ── Internal helpers ───────────────────────────────────────────────────────

def _adc_to_pct(raw_adc: int) -> float:
    """
    Convert a raw 12-bit ADC reading to a soil moisture percentage.

    The capacitive sensor is inverted: higher ADC = drier soil.
    Result is clamped to [0.0, 100.0].
    """
    if SOIL_DRY_ADC == SOIL_WET_ADC:   # guard division-by-zero
        return 50.0
    pct = (SOIL_DRY_ADC - raw_adc) / (SOIL_DRY_ADC - SOIL_WET_ADC) * 100.0
    return round(max(0.0, min(100.0, pct)), 1)


def _enrich(row: dict) -> dict:
    """
    Compute display-ready fields from a raw database row.

    Adds:
      soil_moisture_pct -- 0-100 float for the dashboard progress bar
      moisture_status   -- human-readable label
      temp_status       -- heat / cool / optimal label
      timestamp_human   -- same as timestamp (already a string from SQLite)
      source            -- always 'esp32' for DB-backed readings
    """
    soil_pct = _adc_to_pct(row["soil_moisture"])
    temp     = float(row["temperature"])

    # Moisture status
    if soil_pct < 30:
        moisture_status = "Dry - Irrigation Needed"
    elif soil_pct < 70:
        moisture_status = "Optimal"
    else:
        moisture_status = "Wet - Reduce Watering"

    # Temperature status
    if temp > 35:
        temp_status = "Heat Stress Risk"
    elif temp < 25:
        temp_status = "Cool - Monitor for Disease"
    else:
        temp_status = "Optimal"

    return {
        "id":                row["id"],
        "temperature":       round(temp, 1),
        "humidity":          round(float(row["humidity"]), 1),
        "soil_moisture":     row["soil_moisture"],   # raw ADC  (for records)
        "soil_moisture_pct": soil_pct,               # 0-100 %  (for UI)
        "rain":              row.get("rain", 1),
        "moisture_status":   moisture_status,
        "temp_status":       temp_status,
        "timestamp":         row["timestamp"],
        "timestamp_human":   row["timestamp"],
        "source":            "esp32"
    }


# ── Public API ─────────────────────────────────────────────────────────────

def get_sensor_data() -> dict:
    """
    Return the latest sensor reading from SQLite, enriched with display fields.

    If the database is empty (ESP32 not yet connected) returns a sentinel dict
    with error='no_data' so the frontend can show a friendly waiting message.
    """
    row = get_latest_reading()
    if row is None:
        return {
            "error":   "no_data",
            "message": "No sensor readings yet. Waiting for ESP32...",
            "source":  "none"
        }
    return _enrich(row)


def update_sensor_data(
    temperature:   float,
    humidity:      float,
    soil_moisture: int,
    rain:          int = 1
) -> dict:
    """
    Called when ESP32 POSTs real sensor data via POST /api/sensor-data.
    Inserts one row into SQLite, then returns the enriched reading.

    Args:
        temperature   : degrees Celsius from DHT22
        humidity      : relative humidity % from DHT22
        soil_moisture : raw 12-bit ADC value from capacitive sensor
        rain          : 0 = rain detected, 1 = no rain

    Returns:
        Enriched sensor dict ready to JSON-serialise.
    """
    insert_reading(temperature, humidity, soil_moisture, rain)
    row = get_latest_reading()   # re-fetch so we get the DB-generated timestamp + id
    return _enrich(row)
