// ============================================================
//  crop_monitor.ino  --  ESP32 Sensor Data Poster
//  AI-Driven IoT Crop Monitoring System
// ============================================================
//
//  Sensors:
//    DHT22  (Temp + Humidity)    -> GPIO 4
//    Soil Moisture (Analog AO)   -> GPIO 34
//    Rain Sensor   (Digital DO)  -> GPIO 27
//
//  Every 30 seconds, reads all sensors and sends an
//  HTTP POST to the Flask backend with this JSON payload:
//    {
//      "temperature":   28.6,
//      "humidity":      71.2,
//      "soil_moisture": 1834,
//      "rain":          0
//    }
//
//  Libraries required (install via Arduino Library Manager):
//    - DHT sensor library by Adafruit
//    - Adafruit Unified Sensor
//    - ArduinoJson by Benoit Blanchon
//    - HTTPClient  (bundled with ESP32 Arduino core)
//
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ── WiFi Credentials ─────────────────────────────────────────────────────
//  Change these to match your local network:
const char* WIFI_SSID     = "Airtel_Yallur-WiFi";
const char* WIFI_PASSWORD = "sky_1959";

// ── Flask Server URL ──────────────────────────────────────────────────────
//  Replace with your PC's local IP address.
//  Find it by running: ipconfig   (look for IPv4 Address under your Wi-Fi adapter)
//  Example: "http://192.168.1.10:5000/api/sensor-data"
const char* SERVER_URL = "http://192.168.1.5:5000/api/sensor-data";

// ── Pin Definitions ───────────────────────────────────────────────────────
#define DHT_PIN      4    // DHT22 data line
#define DHT_TYPE     DHT22
#define SOIL_PIN     34   // Capacitive soil moisture -- analog input
#define RAIN_PIN     27   // Rain sensor digital output

// ── Timing ────────────────────────────────────────────────────────────────
const unsigned long SEND_INTERVAL_MS = 30000UL;  // 30 seconds between POSTs

// ── Objects ───────────────────────────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastSendTime = 0;


// ════════════════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("=====================================================");
  Serial.println("  CropSense AI  --  ESP32 Sensor Node");
  Serial.println("=====================================================");

  // Initialise sensors
  dht.begin();
  pinMode(RAIN_PIN, INPUT);
  // GPIO 34 is input-only, no pinMode needed for analog

  // Connect to WiFi
  Serial.print("  Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (++attempts > 40) {
      Serial.println("\n  [ERROR] WiFi connection failed. Rebooting in 5s...");
      delay(5000);
      ESP.restart();
    }
  }

  Serial.println();
  Serial.println("  [OK] WiFi Connected!");
  Serial.print  ("  [OK] IP Address : ");
  Serial.println(WiFi.localIP());
  Serial.print  ("  [OK] Server URL : ");
  Serial.println(SERVER_URL);
  Serial.println("=====================================================");
  Serial.println();
}


// ════════════════════════════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();

  // Send immediately on first iteration, then every SEND_INTERVAL_MS
  if (lastSendTime == 0 || (now - lastSendTime >= SEND_INTERVAL_MS)) {
    lastSendTime = now;
    readAndPost();
  }
}


// ════════════════════════════════════════════════════════════════════════════
void readAndPost() {
  Serial.println("--- Reading Sensors ---");

  // ── DHT22: Temperature & Humidity ────────────────────────────────────────
  float temperature = dht.readTemperature();   // Celsius
  float humidity    = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("  [WARN] DHT22 read failed -- skipping this cycle.");
    Serial.println("  Check wiring: DATA -> GPIO 4, VCC -> 3.3V, GND -> GND");
    return;
  }

  // ── Capacitive Soil Moisture Sensor (Analog) ──────────────────────────────
  // GPIO 34 is ADC1_CH6.  12-bit ADC -> range 0-4095.
  // Higher reading = drier soil (inverted).
  int soilRaw = analogRead(SOIL_PIN);

  // ── Rain Sensor (Digital) ─────────────────────────────────────────────────
  // DO pin: LOW (0) = rain detected, HIGH (1) = no rain
  int rainStatus = digitalRead(RAIN_PIN);

  // ── Print to Serial Monitor ───────────────────────────────────────────────
  Serial.printf("  Temperature  : %.1f C\n",  temperature);
  Serial.printf("  Humidity     : %.1f %%\n", humidity);
  Serial.printf("  Soil ADC raw : %d\n",      soilRaw);
  Serial.printf("  Rain pin     : %d  (%s)\n",
    rainStatus,
    rainStatus == 0 ? "Rain Detected" : "No Rain");

  // ── Build JSON Payload ────────────────────────────────────────────────────
  StaticJsonDocument<256> doc;
  doc["temperature"]   = round(temperature * 10) / 10.0;
  doc["humidity"]      = round(humidity    * 10) / 10.0;
  doc["soil_moisture"] = soilRaw;
  doc["rain"]          = rainStatus;

  String payload;
  serializeJson(doc, payload);
  Serial.print  ("  Payload      : ");
  Serial.println(payload);

  // ── Check WiFi ────────────────────────────────────────────────────────────
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("  [WARN] WiFi lost -- attempting reconnect...");
    WiFi.reconnect();
    delay(4000);
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("  [ERROR] Reconnect failed -- skipping this cycle.");
      return;
    }
    Serial.println("  [OK] WiFi reconnected.");
  }

  // ── HTTP POST ─────────────────────────────────────────────────────────────
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);   // 10-second timeout

  int httpCode = http.POST(payload);

  if (httpCode == 201) {
    Serial.println("  [OK] Data posted successfully (HTTP 201)");
  } else if (httpCode > 0) {
    Serial.printf ("  [WARN] Unexpected HTTP %d\n", httpCode);
    Serial.print  ("  Response: ");
    Serial.println(http.getString());
  } else {
    Serial.printf ("  [ERROR] POST failed: %s\n",
      http.errorToString(httpCode).c_str());
  }

  http.end();
  Serial.printf("\n  Next reading in %lu seconds...\n\n",
    SEND_INTERVAL_MS / 1000);
}
