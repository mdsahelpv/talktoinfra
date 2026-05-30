"""CLI configuration management."""

import json
import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".talktoinfra"
CONFIG_FILE = CONFIG_DIR / "config.json"


class CLIConfig:
    def __init__(self):
        self._data = self._load()

    @property
    def orchestrator_url(self) -> str:
        return self._data.get("orchestrator_url", os.getenv("TALKTOINFRA_URL", "http://localhost:8000"))

    @property
    def api_key(self) -> str:
        return self._data.get("api_key", os.getenv("TALKTOINFRA_API_KEY", ""))

    @property
    def default_session_id(self) -> str:
        return self._data.get("default_session_id", "")

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self._data, indent=2))
