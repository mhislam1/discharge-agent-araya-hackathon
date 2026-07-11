"""Env-driven config. Everything optional; missing pieces degrade gracefully
(see AGENTS.md invariant #4)."""
import json
import os
from pathlib import Path

try:  # optional nicety
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent

# --- Twilio ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")   # the number we bought
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")          # ngrok https URL, no trailing slash
VOICE_MODE = os.getenv("VOICE_MODE", "gather")  # gather | relay

# --- Escalation targets (verified numbers on a trial account!) ---
COORDINATOR_PHONE = os.getenv("COORDINATOR_PHONE", "")      # AMBER
NURSE_PHONE = os.getenv("NURSE_PHONE", "")                  # RED

# --- LLM adapter (see docs/ARCHITECTURE.md) ---
# one of: regex | ollama | groq | gemini_api
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "regex")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")       # or a MedGemma build
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "")                    # pick a small fast open model on the day
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "1.5"))    # voice latency budget


def load_patients() -> dict:
    """patients.json ships with FAKE numbers (the repo is public). Real demo
    phones live in .env as PATIENT_PHONE_<ID>, e.g. PATIENT_PHONE_HAROLD."""
    with open(BASE_DIR / "data" / "patients.json") as f:
        patients = json.load(f)
    for pid, p in patients.items():
        p["phone"] = os.getenv(f"PATIENT_PHONE_{pid.upper()}", p["phone"])
    return patients
