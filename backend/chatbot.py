"""
==============================================================
 chatbot.py  --  AI Chatbot via NVIDIA API
 AI-Driven IoT Crop Monitoring System
==============================================================
 Model  : google/gemma-4-31b-it  (or as set in NVIDIA_MODEL)
 API    : https://integrate.api.nvidia.com/v1
 SDK    : openai >= 2.0 (OpenAI-compatible client)
 Role   : Takes user query + sensor readings
          -> Returns smart agricultural advice
==============================================================
"""

import httpx
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# ── NVIDIA API Configuration ────────────────────────────────────────────────
# Read fresh on every call so .env changes take effect after Flask restart
# without needing to change module-level state.

def _get_nvidia_config() -> tuple:
    """Return (api_key, base_url, model_name) read live from environment."""
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
    return (
        os.getenv("NVIDIA_API_KEY",  ""),
        os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        os.getenv("NVIDIA_MODEL",    "meta/llama-3.1-8b-instruct"),
    )


def _get_client() -> tuple:
    """
    Build a fresh OpenAI-compatible client each call.
    Reads API key and base URL live from .env so no restart is needed
    when credentials change.
    Returns (client, model_name).
    Raises RuntimeError if the key is absent or still a placeholder.
    """
    api_key, base_url, model_name = _get_nvidia_config()

    if not api_key or api_key.strip() in ("", "nvapi-your-key-here"):
        raise RuntimeError(
            "[ERROR] NVIDIA_API_KEY is missing or still set to the placeholder value.\n"
            "  1. Open backend/.env\n"
            "  2. Set NVIDIA_API_KEY=nvapi-<your-real-key>\n"
            "  3. Save the file and try again (no Flask restart needed)"
        )

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=httpx.Client(
            timeout=httpx.Timeout(
                connect=10.0,
                read=90.0,
                write=10.0,
                pool=5.0
            )
        )
    )
    return client, model_name


# ── Prompt builder ──────────────────────────────────────────────────────────

def build_system_prompt(sensor: dict) -> str:
    """
    Build the system prompt injecting current sensor values.
    Uses soil_moisture_pct (0-100 %) for human-readable context.
    Handles the no_data sentinel gracefully.
    """
    no_data   = sensor.get("error") == "no_data"
    soil_pct  = sensor.get("soil_moisture_pct", sensor.get("soil_moisture", "N/A"))

    if no_data:
        sensor_block = "  No sensor data available yet (ESP32 not connected)."
    else:
        sensor_block = (
            f"  - Soil Moisture : {soil_pct}%  ({sensor.get('moisture_status', '')})\n"
            f"  - Temperature   : {sensor.get('temperature', 'N/A')} C  ({sensor.get('temp_status', '')})\n"
            f"  - Humidity      : {sensor.get('humidity', 'N/A')}%\n"
            f"  - Reading Time  : {sensor.get('timestamp_human', 'N/A')}"
        )

    return (
        "You are an expert agricultural AI assistant helping farmers monitor their crops in real time.\n\n"
        "Current field sensor readings:\n"
        f"{sensor_block}\n\n"
        "Your role:\n"
        "1. Answer the farmer's question clearly and simply.\n"
        "2. Reference the sensor values when relevant to give context-aware advice.\n"
        "3. Identify potential crop stress, disease risks, or irrigation needs based on the data.\n"
        "4. Give 2-3 short, actionable recommendations.\n"
        "5. Keep language simple -- the farmer may not be technically expert.\n"
        "6. If sensor values are outside optimal range, clearly flag it.\n\n"
        "Optimal ranges for reference:\n"
        "  - Soil Moisture : 40-70%  (crop-dependent)\n"
        "  - Temperature   : 20-30 C for most crops\n"
        "  - Humidity      : 50-80%\n"
    )


# ── Public API ──────────────────────────────────────────────────────────────

def get_chatbot_response(user_query: str, sensor: dict) -> str:
    """
    Send user query + sensor context to NVIDIA API.
    Returns the AI's agricultural advisory response as a plain string.

    Uses max_tokens (correct for openai SDK v2 with NVIDIA NIM).
    Falls back to a friendly error string on any exception so the
    Flask route never returns a 500.

    Args:
        user_query (str)  : The farmer's question
        sensor     (dict) : Latest sensor reading from get_sensor_data()

    Returns:
        str: AI response text, or a friendly error message starting with [!]
    """
    try:
        client, model_name = _get_client()
        system_prompt = build_system_prompt(sensor)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_query}
            ],
            temperature=0.6,
            top_p=0.9,
            max_tokens=300, 
            reasoning_effort="low",    # NOTE: use max_tokens, not max_completion_tokens
        )

        return response.choices[0].message.content.strip()

    except RuntimeError as exc:
        # API key not configured
        return f"[!] Configuration error: {exc}"

    except Exception as exc:
        error_msg = str(exc)

        if "401" in error_msg or "Unauthorized" in error_msg:
            return "[!] API key error. Please check your NVIDIA API key in backend/.env"
        elif "404" in error_msg:
            return (
                f"[!] Model '{MODEL_NAME}' not found on NVIDIA NIM.\n"
                "Check NVIDIA_MODEL in your .env file.\n"
                "Valid options: google/gemma-4-31b-it, meta/llama-3.1-8b-instruct"
            )
        elif "rate" in error_msg.lower():
            return "[!] Rate limit reached. Please wait a moment and try again."
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return (
                "[!] Request timed out. The NVIDIA API is slow right now.\n"
                "Please try again in a moment."
            )
        elif "connect" in error_msg.lower() or "connection" in error_msg.lower():
            return "[!] Cannot reach NVIDIA API. Check your internet connection."
        else:
            return f"[!] Chatbot error: {error_msg}"

