"""
config.py -- Central configuration for the Support Triage Agent.
Supports both Anthropic Claude and Google Gemini (free tier).
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

# -- API --
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

# Pick provider: prefer Gemini (free), fallback to Anthropic
if GEMINI_API_KEY:
    LLM_PROVIDER = "gemini"
elif ANTHROPIC_API_KEY:
    LLM_PROVIDER = "anthropic"
else:
    LLM_PROVIDER = "none"

MODEL_GEMINI: str = "gemini-2.0-flash"   # free tier, 15 RPM
MODEL_ANTHROPIC: str = "claude-sonnet-4-20250514"
MAX_TOKENS: int = 1500
TEMPERATURE: float = 0.0

# -- Auth / Session --
FLASK_SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", "super-secret-default-key-for-orchestra")
GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# -- Paths --
CODE_DIR    = Path(__file__).resolve().parent
ROOT_DIR    = CODE_DIR.parent
DATA_DIR    = ROOT_DIR / "data"
TICKETS_DIR = ROOT_DIR / "support_tickets"
INPUT_CSV   = TICKETS_DIR / "support_tickets.csv"
OUTPUT_CSV  = TICKETS_DIR / "output.csv"

# -- Retrieval --
TOP_K_DOCS    : int = 8
CHUNK_SIZE    : int = 350
CHUNK_OVERLAP : int = 50
MIN_CHUNK_WORDS: int = 12

# -- Reproducibility --
RANDOM_SEED: int = 42

# -- Output constraints --
VALID_STATUSES      = frozenset({"replied", "escalated"})
VALID_REQUEST_TYPES = frozenset({"product_issue", "feature_request", "bug", "invalid"})
KNOWN_COMPANIES     = frozenset({"HackerRank", "Claude", "Visa"})

# -- Rate limit --
REQUEST_DELAY_SECS: float = 0.1  # Fast bursts, let agent.py retry logic handle 429 rate limits
