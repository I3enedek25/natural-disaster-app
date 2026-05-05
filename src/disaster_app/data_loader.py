from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
LOOKBACK_DAYS = 10000
CACHE_MAX_AGE_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 30
CACHE_SCHEMA_VERSION = "v2"

DISASTER_TYPE_CONFIG: dict[str, str] = {
    "severeStorms": "Tornádók és hurrikánok",
    "volcanoes": "Vulkánkitörések",
    "floods": "Árvizek",
    "landslides": "Lavinák / földcsuszamlások",
    "earthquakes": "Földrengések",
}


def _flatten_coordinate_pairs(value: Any) -> list[tuple[float, float]]:
    if isinstance(value, (list, tuple)):
        if (
            len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):
            return [(float(value[0]), float(value[1]))]

        pairs: list[tuple[float, float]] = []
        for item in value:
            pairs.extend(_flatten_coordinate_pairs(item))
        return pairs

    return []


def extract_centroid(coordinates: Any) -> tuple[float, float] | None:
    points = _flatten_coordinate_pairs(coordinates)
    if not points:
        return None

    lon = sum(point[0] for point in points) / len(points)
    lat = sum(point[1] for point in points) / len(points)
    return lon, lat


def normalize_events(
    events: Iterable[dict[str, Any]],
    category_id: str,
    disaster_label: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event in events:
        for geometry in event.get("geometry", []):
            centroid = extract_centroid(geometry.get("coordinates"))
            if centroid is None:
                continue

            lon, lat = centroid
            rows.append(
                {
                    "category_id": category_id,
                    "disaster_label": disaster_label,
                    "event_id": event.get("id"),
                    "event_title": event.get("title"),
                    "date": geometry.get("date"),
                    "closed": event.get("closed"),
                    "lat": lat,
                    "lon": lon,
                    "magnitude": geometry.get("magnitudeValue"),
                    "magnitude_unit": geometry.get("magnitudeUnit"),
                }
            )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    frame["date"] = pd.to_datetime(frame["date"], utc=True, errors="coerce")
    frame["closed"] = pd.to_datetime(frame["closed"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["date", "lat", "lon"]).reset_index(drop=True)
    return frame


def fetch_events_for_category(category_id: str, days: int = LOOKBACK_DAYS, limit: int = 5000) -> list[dict[str, Any]]:
    response = requests.get(
        EONET_EVENTS_URL,
        params={
            "status": "all",
            "category": category_id,
            "days": days,
            "limit": limit,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    return payload.get("events", [])


def build_dataset(days: int = LOOKBACK_DAYS, limit: int = 5000) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for category_id, disaster_label in DISASTER_TYPE_CONFIG.items():
        events = fetch_events_for_category(category_id=category_id, days=days, limit=limit)
        normalized = normalize_events(events=events, category_id=category_id, disaster_label=disaster_label)
        if not normalized.empty:
            frames.append(normalized)

    if not frames:
        return pd.DataFrame(
            columns=[
                "category_id",
                "disaster_label",
                "event_id",
                "event_title",
                "date",
                "closed",
                "lat",
                "lon",
                "magnitude",
                "magnitude_unit",
            ]
        )

    result = pd.concat(frames, ignore_index=True)
    return result.sort_values("date").reset_index(drop=True)


def default_cache_path(days: int = LOOKBACK_DAYS, limit: int = 5000) -> Path:
    filename = f"eonet_events_days{days}_limit{limit}_{CACHE_SCHEMA_VERSION}.csv"
    return Path(__file__).resolve().parents[2] / "data" / "cache" / filename


def _cache_has_required_columns(frame: pd.DataFrame) -> bool:
    required_columns = {
        "category_id",
        "disaster_label",
        "event_id",
        "event_title",
        "date",
        "closed",
        "lat",
        "lon",
        "magnitude",
        "magnitude_unit",
    }
    return required_columns.issubset(set(frame.columns))


def cache_is_fresh(path: Path, max_age_hours: int = CACHE_MAX_AGE_HOURS) -> bool:
    if not path.exists():
        return False

    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - modified_at) < timedelta(hours=max_age_hours)


def load_events_dataframe(
    force_refresh: bool = False,
    cache_path: Path | None = None,
    days: int = LOOKBACK_DAYS,
    limit: int = 5000,
) -> pd.DataFrame:
    target_cache_path = cache_path or default_cache_path(days=days, limit=limit)
    target_cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not force_refresh and cache_is_fresh(target_cache_path):
        try:
            cached = pd.read_csv(target_cache_path, parse_dates=["date", "closed"])
            if _cache_has_required_columns(cached):
                cached["date"] = pd.to_datetime(cached["date"], utc=True, errors="coerce")
                cached["closed"] = pd.to_datetime(cached["closed"], utc=True, errors="coerce")
                return cached
        except Exception:
            pass

    refreshed = build_dataset(days=days, limit=limit)
    refreshed.to_csv(target_cache_path, index=False)
    return refreshed

