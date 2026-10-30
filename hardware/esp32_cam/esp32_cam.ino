/*
  ============================================================
   esp32_cam.ino  --  ESP32-CAM Firmware
   AI-Driven IoT Crop Monitoring System
  ============================================================
   Board  : AI Thinker ESP32-CAM
   Camera : OV2640 (GRAYSCALE -> JPEG for transport)

   Endpoints  (port 80):
     GET /          -> HTML page with live stream viewer
     GET /capture   -> Returns one still JPEG (image/jpeg)

   Streaming (port 81):
     GET /stream    -> MJPEG multipart stream

   Pin mapping: AI Thinker standard
  ============================================================
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// WiFi Credentials
const char* ssid     = "Moto";
const char* password = "123456789";

// Servers
WebServer   server(80);       // /  and  /capture
WiFiServer  streamServer(81); // MJPEG stream

// AI Thinker ESP32-CAM Pin Map
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Camera Initialisation
void startCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk  = XCLK_GPIO_NUM;
  config.pin_pclk  = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href  = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn  = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_GRAYSCALE;
  config.frame_size   = FRAMESIZE_QVGA;   // 320 x 240
  config.jpeg_quality = 12;
  config.fb_count     = 1;
  config.grab_mode    = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    while (true) delay(1000);
  }
  Serial.println("[CAM] Camera ready");
}

// Route: GET /
void handleRoot() {
  String ip   = WiFi.localIP().toString();
  String html =
    "<html><head>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32-CAM</title>"
    "<style>body{font-family:sans-serif;text-align:center;background:#111;color:#eee}"
    "img{max-width:100%;border:2px solid #3fb950;border-radius:8px;margin-top:1rem}"
    "a{color:#3fb950}</style>"
    "</head><body>"
    "<h2>ESP32-CAM Live Stream</h2>"
    "<img src='http://" + ip + ":81/stream'><br><br>"
    "<a href='/capture'>Take still (JPEG)</a>"
    "</body></html>";
  server.send(200, "text/html", html);
}

// Route: GET /capture
// Capture one frame, convert GRAYSCALE -> JPEG, return as image/jpeg.
void handleCapture() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    server.send(503, "text/plain", "Camera capture failed");
    Serial.println("[CAM] Capture failed");
    return;
  }

  uint8_t* jpg_buf = nullptr;
  size_t   jpg_len = 0;
  bool ok = frame2jpg(fb, 80, &jpg_buf, &jpg_len);
  esp_camera_fb_return(fb);

  if (!ok || jpg_buf == nullptr) {
    server.send(503, "text/plain", "JPEG conversion failed");
    Serial.println("[CAM] JPEG conversion failed");
    return;
  }

  server.sendHeader("Cache-Control", "no-store");
  server.sendHeader("Content-Disposition", "inline; filename=\"capture.jpg\"");
  server.send_P(200, "image/jpeg",
                reinterpret_cast<const char*>(jpg_buf),
                static_cast<int>(jpg_len));

  free(jpg_buf);
  Serial.printf("[CAM] Capture sent (%u bytes)\n", jpg_len);
}

// MJPEG Stream (port 81)
void streamVideo() {
  WiFiClient client = streamServer.available();
  if (!client) return;

  Serial.println("[CAM] Stream client connected");
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
  client.println();

  while (client.connected()) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) { Serial.println("[CAM] Stream: capture failed"); continue; }

    uint8_t* jpg_buf = nullptr;
    size_t   jpg_len = 0;
    if (frame2jpg(fb, 40, &jpg_buf, &jpg_len)) {
      client.printf("--frame\r\n");
      client.printf("Content-Type: image/jpeg\r\n");
      client.printf("Content-Length: %u\r\n\r\n", jpg_len);
      client.write(jpg_buf, jpg_len);
      client.printf("\r\n");
      free(jpg_buf);
    }
    esp_camera_fb_return(fb);
    delay(30);
  }
  Serial.println("[CAM] Stream client disconnected");
}

void streamTask(void* pvParameters) {
  while (true) { streamVideo(); vTaskDelay(1); }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  startCamera();

  WiFi.begin(ssid, password);
  Serial.print("[NET] Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println();
  Serial.println("[NET] WiFi connected");
  Serial.print("[NET] IP: "); Serial.println(WiFi.localIP());
  Serial.println("[NET] Dashboard : http://" + WiFi.localIP().toString() + "/");
  Serial.println("[NET] Capture   : http://" + WiFi.localIP().toString() + "/capture");
  Serial.println("[NET] Stream    : http://" + WiFi.localIP().toString() + ":81/stream");

  server.on("/",        handleRoot);
  server.on("/capture", handleCapture);   // new still-image endpoint
  server.begin();

  streamServer.begin();

  xTaskCreatePinnedToCore(streamTask, "streamTask", 8192, NULL, 1, NULL, 0);
}

void loop() {
  server.handleClient();
}
