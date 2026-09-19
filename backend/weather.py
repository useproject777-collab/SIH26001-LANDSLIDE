from datetime import datetime, timedelta
from typing import Any

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SINGLE = 15
TIMEOUT_BATCH = 30

HOURLY_FIELDS = ",".join(
    [
        "rain",
        "precipitation",
        "precipitation_probability",
        "soil_moisture_0_to_7cm",
    ]
)
CURRENT_FIELDS = ",".join(
    [
        "temperature_2m",
        "rain",
        "precipitation",
    ]
)


def _parse_local_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _series_window_sum(
    times: list[str],
    values: list[Any],
    current_time: datetime | None,
    hours: int,
) -> float:
    if not times or current_time is None:
        numeric = [_safe_number(v) for v in values]
        return round(sum(numeric[-hours:]), 2)

    start = current_time - timedelta(hours=hours)
    selected = []
    for raw_time, value in zip(times, values):
        parsed = _parse_local_time(raw_time)
        if parsed is None:
            continue
        if start < parsed <= current_time:
            selected.append(_safe_number(value))
    return round(sum(selected), 2)


def process_weather_response(data: dict[str, Any]) -> dict[str, Any]:
    current = data.get("current", {}) or {}
    hourly = data.get("hourly", {}) or {}

    times = hourly.get("time", []) or []
    rain = hourly.get("rain", []) or []
    precipitation = hourly.get("precipitation", []) or []
    precipitation_probability = hourly.get("precipitation_probability", []) or []
    soil_moisture = hourly.get("soil_moisture_0_to_7cm", []) or []

    current_time_str = current.get("time")
    current_time = _parse_local_time(current_time_str)

    # Select the latest soil moisture at or before the current weather time.
    latest_soil = None
    latest_probability = 0.0
    forecast_rain_6h = 0.0

    future_rain = []
    if current_time is not None:
        for raw_time, rain_value in zip(times, rain):
            parsed = _parse_local_time(raw_time)
            if parsed is None:
                continue
            numeric = _safe_number(rain_value)
            if parsed <= current_time:
                if soil_moisture:
                    idx = times.index(raw_time)
                    if idx < len(soil_moisture):
                        latest_soil = _safe_number(soil_moisture[idx])
                continue
            if parsed <= current_time + timedelta(hours=6):
                future_rain.append(numeric)
                try:
                    idx = times.index(raw_time)
                    if idx < len(precipitation_probability):
                        latest_probability = max(
                            latest_probability,
                            _safe_number(precipitation_probability[idx]),
                        )
                except ValueError:
                    pass
    if latest_soil is None and soil_moisture:
        latest_soil = _safe_number(soil_moisture[-1])

    # Fallback for precipitation probability if no future window matched.
    if not future_rain:
        future_rain = [_safe_number(v) for v in rain[-6:]]
        latest_probability = max(
            [_safe_number(v) for v in precipitation_probability[-6:]],
            default=0.0,
        )

    forecast_rain_6h = round(sum(future_rain), 2)

    return {
        "temperature": _safe_number(current.get("temperature_2m")),
        "current_rain_mm": _safe_number(current.get("rain")),
        "precipitation_mm": _safe_number(current.get("precipitation")),
        "rainfall_1h": _series_window_sum(times, rain, current_time, 1),
        "rainfall_3h": _series_window_sum(times, rain, current_time, 3),
        "rainfall_6h": _series_window_sum(times, rain, current_time, 6),
        "rainfall_24h": _series_window_sum(times, rain, current_time, 24),
        "forecast_rain_6h": forecast_rain_6h,
        "precipitation_probability_max": round(latest_probability, 1),
        "soil_moisture_0_7cm": latest_soil,
        "time": current_time_str,
    }


def _build_params(latitude: str, longitude: str) -> dict[str, Any]:
    return {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_FIELDS,
        "hourly": HOURLY_FIELDS,
        "past_hours": 24,
        "forecast_hours": 24,
        "timezone": "Asia/Kolkata",
        "forecast_days": 2,
    }


def get_live_weather(latitude: float, longitude: float) -> dict[str, Any]:
    params = _build_params(str(latitude), str(longitude))
    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=TIMEOUT_SINGLE,
    )
    response.raise_for_status()
    return process_weather_response(response.json())


def get_live_weather_batch(locations: list[Any]) -> list[dict[str, Any]]:
    if not locations:
        return []

    # Keep URL size manageable. 100 is supported by Open-Meteo for many variables,
    # but smaller chunks make failure handling easier.
    chunk_size = 50
    results: list[dict[str, Any]] = []

    for start in range(0, len(locations), chunk_size):
        chunk = locations[start : start + chunk_size]
        latitudes = ",".join(str(location.latitude) for location in chunk)
        longitudes = ",".join(str(location.longitude) for location in chunk)
        params = _build_params(latitudes, longitudes)

        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=TIMEOUT_BATCH,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            payload = [payload]

        for location, weather_payload in zip(chunk, payload):
            parsed = process_weather_response(weather_payload)
            parsed["location_id"] = location.id
            results.append(parsed)

    return results
