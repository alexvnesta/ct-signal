from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog" / "indicators.yaml"
SEEDS_PATH = ROOT / "data" / "seeds.yaml"
ASKED_LOG_PATH = ROOT / "data" / "asked_log.json"
OUTPUT_DIR = ROOT / "output"
FIXTURES_DIR = ROOT / "fixtures"


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

DC_API_KEY = os.environ.get("DC_API_KEY", "")
DC_ENDPOINT = "https://api.datacommons.org/v2/observation"
SOCRATA_PORTAL = "https://data.ct.gov"

CT_FEEDS = [
    "https://ctmirror.org/feed/",
    "https://news.google.com/rss/search?q=connecticut&hl=en-US&gl=US&ceid=US:en",
]
NATIONAL_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.pbs.org/newshour/feeds/rss/headlines",
]

UA = {"User-Agent": "Mozilla/5.0 (CTSignal/0.1; hackathon prototype)"}

SOCRATA_TOKEN = os.environ.get("SOCRATA_TOKEN", "")
if SOCRATA_TOKEN:
    UA["X-App-Token"] = SOCRATA_TOKEN
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")
_DEFAULT_MODELS = "gemini-3.1-flash-lite,gemini-flash-lite-latest,gemini-2.5-flash-lite,gemini-3.8-flash"
_GEMINI_MODEL_LIST = f"{GEMINI_MODEL},{_DEFAULT_MODELS}" if GEMINI_MODEL else _DEFAULT_MODELS
GEMINI_MODELS = [m.strip() for m in _GEMINI_MODEL_LIST.split(",") if m.strip()]


def gemini_endpoint(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
