from __future__ import annotations

import json
import os
from pathlib import Path


APP_STATE_DIR = Path(os.environ.get("APPDATA", Path.home())) / "dispatcher-desktop"
APP_STATE_FILE = APP_STATE_DIR / "state.json"


def load_app_state() -> dict:
    if not APP_STATE_FILE.exists():
        return {}
    try:
        return json.loads(APP_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_app_state(state: dict) -> None:
    APP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    APP_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
