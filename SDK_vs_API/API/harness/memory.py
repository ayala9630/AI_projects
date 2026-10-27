import json
import os
import threading
from pathlib import Path
from typing import Any

MEMORY_FILE = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "data"
    / "memory.json"
)

_LOCK = threading.RLock()

DEFAULT_MEMORY: dict[str, Any] = {
    "preferences": {
        "default_city": None,
        "minimum_capacity": 0,
        "required_features": [],
    }
}


def load_memory() -> dict[str, Any]:
    """Load persistent preferences from disk."""
    with _LOCK:
        if not MEMORY_FILE.exists():
            print("[memory.py] Memory file not found; using defaults")
            return json.loads(json.dumps(DEFAULT_MEMORY))

        try:
            with MEMORY_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Memory root must be a JSON object")

            preferences = data.get("preferences", {})
            if not isinstance(preferences, dict):
                raise ValueError("'preferences' must be a JSON object")

            print("[memory.py] Loaded preferences")
            return data

        except (json.JSONDecodeError, OSError, ValueError) as exc:
            raise RuntimeError(
                f"Could not load memory from {MEMORY_FILE}: {exc}"
            ) from exc


def save_memory(
    updates: dict[str, Any],
    *,
    replace: bool = False,
) -> dict[str, Any]:
    """
    Update preferences and persist them.

    By default, only supplied keys are updated.
    With replace=True, the preferences object is replaced entirely.
    """
    if not isinstance(updates, dict):
        raise TypeError("updates must be a dictionary")

    with _LOCK:
        current = load_memory()
        old_preferences = current.get("preferences", {})

        if replace:
            new_preferences = dict(updates)
        else:
            new_preferences = {**old_preferences, **updates}

        current["preferences"] = new_preferences
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        temporary_file = MEMORY_FILE.with_suffix(".tmp")

        try:
            with temporary_file.open("w", encoding="utf-8") as file:
                json.dump(
                    current,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_file, MEMORY_FILE)

        finally:
            if temporary_file.exists():
                temporary_file.unlink()

        print("[memory.py] Saved preferences")
        return current


def get_relevant_memory(
    request: dict[str, Any],
) -> dict[str, Any]:
    """
    Return only preferences relevant to the current request.

    Explicit values in the current request take precedence over
    saved defaults. This function does not change persistent memory.
    """
    memory = load_memory()
    preferences = memory.get("preferences", {})

    relevant = {
        "default_city": preferences.get("default_city"),
        "minimum_capacity": preferences.get("minimum_capacity", 0),
        "required_features": preferences.get("required_features", []),
    }

    # Current request overrides defaults for this turn only.
    if request.get("city"):
        relevant["default_city"] = request["city"]

    if request.get("min_capacity") is not None:
        relevant["minimum_capacity"] = request["min_capacity"]

    if request.get("required_features") is not None:
        relevant["required_features"] = request["required_features"]

    print("[memory.py] Selected relevant preferences")
    return relevant