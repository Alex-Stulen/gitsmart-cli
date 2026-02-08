import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".gitsmart"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.example.com"
DEFAULT_COMMIT_LANGUAGE = "en"

# API request timeouts (in seconds)
TIMEOUT_DEFAULT = 60.0  # 1 minute - default for all requests
TIMEOUT_COMMIT = 120.0  # 2 minutes - regular commit
TIMEOUT_COMMIT_SMART = 300.0  # 5 minutes - smart commit with grouping
TIMEOUT_REVIEW = 120.0  # 2 minutes - code review
TIMEOUT_ANALYZE = 120.0  # 2 minutes - repository analysis

KNOWN_KEYS = ["api_key", "api_url", "commit_language"]


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_api_key():
    return load_config().get("api_key")


def get_api_url():
    return load_config().get("api_url") or DEFAULT_API_URL


def get_commit_language():
    return load_config().get("commit_language") or DEFAULT_COMMIT_LANGUAGE
