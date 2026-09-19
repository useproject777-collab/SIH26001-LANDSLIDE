from typing import Any


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def calculate_rainfall_score(
    rainfall_1h: float,
    rainfall_3h: float,
    rainfall_6h: float,
    rainfall_24h: float,
) -> int:
    # Prototype index thresholds. Replace/calibrate with authoritative local thresholds
    # when validated rainfall-trigger data are available.
    score_1h = _clamp(rainfall_1h / 20 * 100)
    score_3h = _clamp(rainfall_3h / 50 * 100)
    score_6h = _clamp(rainfall_6h / 80 * 100)
    score_24h = _clamp(rainfall_24h / 150 * 100)
    return round(
        score_1h * 0.15
        + score_3h * 0.20
        + score_6h * 0.25
        + score_24h * 0.40
    )


def calculate_slope_score(slope: float) -> int:
    if slope >= 45:
        return 100
    if slope >= 35:
        return 90
    if slope >= 25:
        return 70
    if slope >= 15:
        return 40
    return 20


def calculate_soil_moisture_score(soil_moisture: float | None) -> int | None:
    if soil_moisture is None:
        return None
    # Prototype normalization for volumetric water content (m³/m³).
    return round(_clamp((soil_moisture / 0.45) * 100))


def calculate_forecast_score(forecast_rain_6h: float | None) -> int | None:
    if forecast_rain_6h is None:
        return None
    return round(_clamp((forecast_rain_6h / 80) * 100))


def calculate_risk(
    rainfall_1h: float,
    rainfall_3h: float,
    rainfall_6h: float,
    rainfall_24h: float,
    slope: float,
    soil_moisture: float | None = None,
    forecast_rain_6h: float | None = None,
) -> dict[str, Any]:
    rainfall_score = calculate_rainfall_score(
        rainfall_1h,
        rainfall_3h,
        rainfall_6h,
        rainfall_24h,
    )
    slope_score = calculate_slope_score(slope)
    soil_score = calculate_soil_moisture_score(soil_moisture)
    forecast_score = calculate_forecast_score(forecast_rain_6h)

    # Keep the established 60/40 prototype weighting when optional model context
    # is unavailable. When available, add small context weights and renormalize.
    components = [
        (rainfall_score, 0.50),
        (slope_score, 0.30),
        (soil_score, 0.10),
        (forecast_score, 0.10),
    ]
    usable = [(score, weight) for score, weight in components if score is not None]
    total_weight = sum(weight for _, weight in usable)
    risk_score = round(sum(score * weight for score, weight in usable) / total_weight)

    if risk_score >= 80:
        risk_level = "CRITICAL"
    elif risk_score >= 60:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "rainfall_score": rainfall_score,
        "slope_score": slope_score,
        "soil_moisture_score": soil_score,
        "forecast_score": forecast_score,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "method": "Configurable prototype risk index; thresholds require local validation",
    }
