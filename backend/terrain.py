import math
from typing import Any

import requests

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
ELEVATION_TIMEOUT = 20


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_elevations(points: list[tuple[float, float]]) -> list[float]:
    if not points:
        return []

    # Open-Meteo Elevation supports up to 100 coordinates per request.
    results: list[float] = []
    for start in range(0, len(points), 100):
        chunk = points[start : start + 100]
        latitudes = ",".join(str(lat) for lat, _ in chunk)
        longitudes = ",".join(str(lon) for _, lon in chunk)

        response = requests.get(
            ELEVATION_URL,
            params={"latitude": latitudes, "longitude": longitudes},
            timeout=ELEVATION_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        results.extend(_to_float(value) for value in data.get("elevation", []))

    return results


def calculate_slope_from_cross(
    latitude: float,
    longitude: float,
    elevations: list[float],
    offset_deg: float,
) -> float:
    # [center, north, south, east, west]
    if len(elevations) < 5:
        return 0.0

    _, north, south, east, west = elevations[:5]

    north_distance = _haversine_m(
        latitude,
        longitude,
        latitude + offset_deg,
        longitude,
    )
    south_distance = _haversine_m(
        latitude,
        longitude,
        latitude - offset_deg,
        longitude,
    )
    east_distance = _haversine_m(
        latitude,
        longitude,
        latitude,
        longitude + offset_deg,
    )
    west_distance = _haversine_m(
        latitude,
        longitude,
        latitude,
        longitude - offset_deg,
    )

    ns_distance = north_distance + south_distance
    ew_distance = east_distance + west_distance

    if ns_distance <= 0 or ew_distance <= 0:
        return 0.0

    dz_dnorth = (north - south) / ns_distance
    dz_deast = (east - west) / ew_distance
    gradient = math.sqrt(dz_dnorth**2 + dz_deast**2)
    slope_degree = math.degrees(math.atan(gradient))
    return round(max(0.0, min(slope_degree, 90.0)), 2)


def get_terrain_profile(latitude: float, longitude: float) -> dict[str, Any]:
    offset = 0.0015  # ~160–170 m around these latitudes
    points = [
        (latitude, longitude),
        (latitude + offset, longitude),
        (latitude - offset, longitude),
        (latitude, longitude + offset),
        (latitude, longitude - offset),
    ]
    elevations = get_elevations(points)
    elevation_m = round(elevations[0], 2) if elevations else None
    slope_degree = calculate_slope_from_cross(
        latitude,
        longitude,
        elevations,
        offset,
    )
    return {
        "elevation_m": elevation_m,
        "slope_degree": slope_degree,
        "source": "Open-Meteo Elevation / Copernicus DEM GLO-90",
        "sample_offset_m": round(_haversine_m(latitude, longitude, latitude + offset, longitude), 1),
    }


def get_terrain_profiles_batch(locations: list[Any]) -> list[dict[str, Any]]:
    if not locations:
        return []

    offset = 0.0015
    points: list[tuple[float, float]] = []
    owners: list[int] = []
    for location in locations:
        points.extend(
            [
                (location.latitude, location.longitude),
                (location.latitude + offset, location.longitude),
                (location.latitude - offset, location.longitude),
                (location.latitude, location.longitude + offset),
                (location.latitude, location.longitude - offset),
            ]
        )
        owners.append(location.id)

    elevations = get_elevations(points)
    profiles = []
    for idx, location in enumerate(locations):
        chunk = elevations[idx * 5 : idx * 5 + 5]
        elevation_m = round(chunk[0], 2) if chunk else None
        slope_degree = calculate_slope_from_cross(
            location.latitude,
            location.longitude,
            chunk,
            offset,
        )
        profiles.append(
            {
                "location_id": location.id,
                "elevation_m": elevation_m,
                "slope_degree": slope_degree,
                "source": "Open-Meteo Elevation / Copernicus DEM GLO-90",
            }
        )
    return profiles
