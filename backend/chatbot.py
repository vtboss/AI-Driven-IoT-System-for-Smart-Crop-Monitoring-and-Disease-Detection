"""
==========================================================
 chatbot.py — AI Chatbot via NVIDIA API
==========================================================
 Model  : google/gemma-4-31b-it
 API    : https://integrate.api.nvidia.com/v1
 SDK    : openai >= 2.0 (OpenAI-compatible client)
 Role   : Takes user query + sensor readings
          → Returns smart agricultural advice
==========================================================
"""

import httpx
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load variables from backend/.env
load_dotenv()

# ──────────────────────────────────────────────
# 🔑 NVIDIA API Configuration (loaded from .env)
# ──────────────────────────────────────────────
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME      = os.getenv("NVIDIA_MODEL",   "google/gemma-4-31b-it")

if not NVIDIA_API_KEY or NVIDIA_API_KEY == "nvapi-your-key-here":
    raise EnvironmentError(
        "\n[ERROR] NVIDIA_API_KEY is missing!\n"
        "  1. Copy backend/.env.example  →  backend/.env\n"
        "  2. Paste your real API key from https://integrate.api.nvidia.com\n"
    )

# Initialize the OpenAI-compatible client pointing to NVIDIA.
# Timeout: 30s to connect, 60s to read response.
# Without a timeout the request can hang indefinitely.
client = OpenAI(
    base_url=NVIDIA_BASE_URL,
    api_key=NVIDIA_API_KEY,
    http_client=httpx.Client(
        timeout=httpx.Timeout(
            connect=10.0,   # max seconds to establish connection
            read=60.0,      # max seconds to wait for response
            write=10.0,
            pool=5.0
        )
    )
)


def build_system_prompt(sensor: dict) -> str:
    """
    Builds the system prompt by injecting current sensor values.
    This gives the AI full context before answering the user query.
    """
    return f"""You are an expert agricultural AI assistant helping farmers monitor their crops.

Current field sensor readings:
  - Soil Moisture : {sensor.get('soil_moisture', 'N/A')}% ({sensor.get('moisture_status', '')})
  - Temperature   : {sensor.get('temperature', 'N/A')}°C ({sensor.get('temp_status', '')})
  - Humidity      : {sensor.get('humidity', 'N/A')}%
  - Reading Time  : {sensor.get('timestamp_human', 'N/A')}

Your role:
1. Answer the farmer's question clearly and simply.
2. Reference the sensor values when relevant to give context-aware advice.
3. Identify potential crop stress, disease risks, or irrigation needs based on the data.
4. Give 2–3 short, actionable recommendations.
5. Keep language simple — the farmer may not be technically expert.
6. If sensor values are outside optimal range, clearly flag it.

Optimal ranges for reference:
  - Soil Moisture : 40–70% (crop-dependent)
  - Temperature   : 20–30°C for most crops
  - Humidity      : 50–80%
"""


def get_chatbot_response(user_query: str, sensor: dict) -> str:
    """
    Sends user query + sensor context to NVIDIA API.
    Returns the AI's agricultural advisory response.

    Args:
        user_query (str): The farmer's question/concern
        sensor     (dict): Latest sensor readings from get_sensor_data()

    Returns:
        str: AI-generated advisory text
    """
    try:
        system_prompt = build_system_prompt(sensor)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_query
                }
            ],
            temperature=0.6,       # Balanced: factual yet natural language
            top_p=0.9,
            max_completion_tokens=512,   # max_tokens renamed in openai v2
        )

        # Extract the text content from the response
        ai_text = response.choices[0].message.content
        return ai_text.strip()

    except Exception as e:
        # Return a user-friendly error instead of crashing
        error_msg = str(e)

        if "401" in error_msg or "Unauthorized" in error_msg:
            return "⚠️ API key error. Please check your NVIDIA API key in the .env file."
        elif "404" in error_msg:
            return (
                "⚠️ Model not found. Check NVIDIA_MODEL in your .env file.\n"
                "Try: meta/llama-3.1-8b-instruct or google/gemma-3-12b-it"
            )
        elif "rate" in error_msg.lower():
            return "⚠️ Rate limit reached. Please wait a moment and try again."
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return "⚠️ Request timed out. The NVIDIA API is slow right now — please try again in a moment."
        elif "connect" in error_msg.lower():
            return "⚠️ Cannot reach NVIDIA API. Check your internet connection."
        else:
            return f"⚠️ Chatbot error: {error_msg}"
