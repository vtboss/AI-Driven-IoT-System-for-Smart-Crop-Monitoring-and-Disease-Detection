"""
==============================================================
 database.py  --  SQLite persistence layer
 AI-Driven IoT Crop Monitoring System
==============================================================
 Provides:
   init_db()           -- Create DB + table on startup
   insert_reading()    -- Store one ESP32 reading
   get_latest_reading() -- Fetch most recent row
   get_history()       -- Fetch last N rows for charts
==============================================================
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Resolve DB path: defaults to backend/sensor_data.db
_DB_FILE = os.getenv("DB_PATH", "sensor_data.db")
DB_PATH  = os.path.join(os.path.dirname(__file__), _DB_FILE)


# ── Schema ─────────────────────────────────────────────────────────────────
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    temperature   REAL     NOT NULL,
    humidity      REAL     NOT NULL,
    soil_moisture INTEGER  NOT NULL,
    rain          INTEGER  NOT NULL DEFAULT 1,
    timestamp     DATETIME DEFAULT (datetime('now','localtime'))
);
"""


# ── Public API ─────────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Create sensor_data.db and the sensor_data table if they do not exist.
    Called once at Flask startup.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_CREATE_TABLE)
    conn.commit()
    conn.close()
    print(f" [DB] Database ready: {DB_PATH}")


def insert_reading(
    temperature:   float,
    humidity:      float,
    soil_moisture: int,
    rain:          int = 1
) -> int:
    """
    Insert one sensor reading.

    Args:
        temperature   : DHT22 temperature in Celsius
        humidity      : DHT22 relative humidity in %
        soil_moisture : Raw ADC value from capacitive sensor (0-4095)
        rain          : 0 = rain detected, 1 = no rain (default 1)

    Returns:
        Row ID of the inserted record.
    """
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensor_data (temperature, humidity, soil_moisture, rain) VALUES (?, ?, ?, ?)",
        (temperature, humidity, soil_moisture, rain)
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_latest_reading() -> dict | None:
    """
    Return the most recent sensor reading as a dict.
    Returns None if the table is empty (no readings yet).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_history(limit: int = 50) -> list[dict]:
    """
    Return the last `limit` readings ordered newest-first.

    Args:
        limit : Maximum number of rows to return (clamped to 1-200)

    Returns:
        List of dicts, each representing one sensor reading.
    """
    limit = max(1, min(limit, 200))
    conn  = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sensor_data ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
