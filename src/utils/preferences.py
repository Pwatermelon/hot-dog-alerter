"""Простое хранение пользовательских настроек."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from src.config import DEFAULT_SOUND_FILE, USER_SETTINGS_PATH


def load_preferences() -> Dict[str, Any]:
    defaults = {"sound_file": DEFAULT_SOUND_FILE}
    if not os.path.exists(USER_SETTINGS_PATH):
        return defaults
    try:
        with open(USER_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return defaults
        sound = data.get("sound_file") or DEFAULT_SOUND_FILE
        if not os.path.exists(sound):
            sound = DEFAULT_SOUND_FILE
        return {"sound_file": sound}
    except (OSError, json.JSONDecodeError):
        return defaults


def save_preferences(prefs: Dict[str, Any]) -> None:
    payload = {
        "sound_file": prefs.get("sound_file") or DEFAULT_SOUND_FILE,
    }
    try:
        with open(USER_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
