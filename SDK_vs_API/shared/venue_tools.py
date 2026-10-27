"""Shared domain tools. All venue data is read from shared/data/venues.json."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
VENUES_PATH = DATA_DIR / "venues.json"

def load_venues() -> list[dict[str, Any]]:
    if not VENUES_PATH.exists():
        return []
    with VENUES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("venues.json must contain a JSON array")
    return data

def search_venues(city: str | None = None, min_capacity: int = 1,
                  required_features: list[str] | None = None) -> list[dict[str, Any]]:
    required = {x.strip().casefold() for x in (required_features or [])}
    results = []
    for venue in load_venues():
        if city and venue.get("city", "").casefold() != city.casefold():
            continue
        if int(venue.get("capacity", 0)) < int(min_capacity):
            continue
        features = {str(x).casefold() for x in venue.get("features", [])}
        if not required.issubset(features):
            continue
        results.append(venue)
    return results

def get_venue_details(venue_id: str) -> dict[str, Any] | None:
    return next((v for v in load_venues() if str(v.get("id")) == str(venue_id)), None)
