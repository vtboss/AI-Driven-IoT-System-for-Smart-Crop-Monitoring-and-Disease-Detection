# 🌾 AI-Driven IoT System for Smart Crop Monitoring & Disease Detection

> **Real-Time Crop Disease Detection and Severity Prediction with Smart Advisory**
> Phase 1 — IoT Sensor Dashboard + NVIDIA AI Chatbot

---

## 📸 Dashboard Preview

| Sensor Dashboard | AI Agricultural Advisor |
|---|---|
| Live soil moisture, temperature & humidity cards | NVIDIA gemma-4-31b-it powered chat advisory |

---

## 🏗️ System Architecture

```
ESP32 (Sensor Node)
    │  WiFi POST /api/esp32-data
    ▼
Flask Backend (Python)          ◄──── .env (API keys, config)
    ├── GET  /dashboard          → Serves frontend HTML
    ├── GET  /api/sensor-data    → Returns sensor readings (JSON)
    └── POST /api/chat           → AI chatbot (NVIDIA API)
            │
            ▼
    NVIDIA API (gemma-4-31b-it)
            │
            ▼
Frontend Dashboard (HTML/CSS/JS)
    ├── Live sensor cards (auto-refresh every 30s)
    ├── Progress bars with color-coded status
    └── AI chat interface with quick prompts
```

---

## ⚡ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/AI-Driven-IoT-System-for-Smart-Crop-Monitoring-and-Disease-Detection.git
cd AI-Driven-IoT-System-for-Smart-Crop-Monitoring-and-Disease-Detection
```

### 2. Set up environment variables
```bash
# Copy the template
cp backend/.env.example backend/.env

# Open backend/.env and paste your NVIDIA API key
# Get your key at: https://integrate.api.nvidia.com
```

Your `backend/.env` should look like:
```env
NVIDIA_API_KEY=nvapi-your-actual-key-here
NVIDIA_MODEL=google/gemma-4-31b-it
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
FLASK_PORT=5000
FLASK_DEBUG=true
```

### 3. Create virtual environment & install dependencies
```bash
# Create venv (recommended)
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — Mac/Linux
source venv/bin/activate

# Install packages
pip install -r backend/requirements.txt
```

### 4. Run the server

**Option A — Windows one-click:**
```
Double-click run.bat
```

**Option B — Manual:**
```bash
python backend/app.py
```

### 5. Open the dashboard
```
http://localhost:5000/dashboard
```

---

## 📁 Project Structure

```
AI-Driven-IoT-System/
│
├── backend/
│   ├── app.py            ← Flask server (routes, frontend serving)
│   ├── sensor_data.py    ← Sensor data module (dummy → ESP32 ready)
│   ├── chatbot.py        ← NVIDIA API chatbot integration
│   ├── requirements.txt  ← Python dependencies
│   ├── .env              ← 🔒 Secrets (NOT in git)
│   └── .env.example      ← ✅ Template (safe to commit)
│
├── frontend/
│   ├── index.html        ← Dashboard UI
│   ├── style.css         ← Dark agricultural theme
│   └── app.js            ← Sensor fetch + chat logic
│
├── .gitignore
├── run.bat               ← Windows one-click start
└── README.md
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check (JSON) |
| `GET` | `/dashboard` | Serve dashboard HTML |
| `GET` | `/api/sensor-data` | Get latest sensor readings |
| `POST` | `/api/chat` | Send query → AI advisory |
| `POST` | `/api/esp32-data` | *(Phase 2)* Receive ESP32 readings |

### Example: Chat API
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Is my soil moisture okay for wheat?"}'
```

```json
{
  "response": "Your soil moisture at 44.3% is within optimal range...",
  "sensor_context": {
    "soil_moisture": 44.3,
    "temperature": 26.1,
    "humidity": 40.4
  }
}
```

---

## 🔧 Hardware Components (Phase 2)

| Component | Role |
|---|---|
| ESP32 / ESP32-CAM | Main microcontroller + WiFi |
| Soil Moisture Sensor | Analog soil water content reading |
| DHT22 | Temperature & humidity |
| OLED SSD1306 | Local display |
| Relay Module | Irrigation control (future) |

---

## 🚀 Deployment (Production)

### Using Gunicorn (Linux/Mac)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

### Environment Variables for Production
```env
FLASK_DEBUG=false          # IMPORTANT: disable debug in production
FLASK_PORT=5000
NVIDIA_API_KEY=nvapi-...
```

### Platforms supported
- **Railway** — connect GitHub repo, set env vars in dashboard
- **Render** — free tier, set start command to `python backend/app.py`
- **Fly.io** — use `fly launch` in project root

---

## 📦 Dependencies

```
flask==3.0.3          Web framework
flask-cors==4.0.1     Cross-origin requests (frontend ↔ backend)
openai>=2.0.0         NVIDIA API client (OpenAI-compatible)
httpx>=0.28.0         HTTP client
python-dotenv==1.0.1  .env file loading
```

---

## 🛣️ Roadmap

- [x] Phase 1 — Flask backend + dummy sensor data
- [x] Phase 1 — NVIDIA AI chatbot integration
- [x] Phase 1 — Live dashboard frontend
- [ ] Phase 2 — ESP32 WiFi sensor data push
- [ ] Phase 2 — ESP32-CAM image capture
- [ ] Phase 3 — ML model for disease detection
- [ ] Phase 3 — Severity prediction
- [ ] Phase 4 — Alert system + notifications

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add: your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

> **Built for:** AI-Driven Smart Agriculture Research
> **Stack:** ESP32 · Python Flask · NVIDIA AI · Vanilla JS