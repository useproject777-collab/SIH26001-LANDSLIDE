from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, initialize_database

from .models import Location

from .risk import calculate_risk

from .terrain import get_terrain_profile, get_terrain_profiles_batch

from .weather import get_live_weather, get_live_weather_batch

from .ml_service import get_model_status, predict_experimental, train_model

from .satellite import satellite_layer_config
app = FastAPI(
    title="NER Landslide Early Warning System",
    description="AI-Based Landslide Risk Monitoring System",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def root():
    return {
        "message": "NER Landslide Early Warning System API is running",
        "version": app.version,
    }


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}


def _round_or_none(value: Any, digits: int = 2):
    if value is None:
        return None
    return round(float(value), digits)


def get_slope(location_id: int, db: Session):
    row = db.execute(
        text(
            """
            SELECT slope_degree, elevation_m, source, recorded_at
            FROM slope_data
            WHERE location_id = :location_id
            ORDER BY recorded_at DESC
            LIMIT 1
            """
        ),
        {"location_id": location_id},
    ).fetchone()
    if not row:
        return {"slope_degree": 0.0, "elevation_m": None, "source": "No stored terrain value", "recorded_at": None}
    return {
        "slope_degree": float(row[0]),
        "elevation_m": float(row[1]) if row[1] is not None else None,
        "source": row[2] or "Stored slope data",
        "recorded_at": row[3].isoformat() if row[3] is not None else None,
    }


def save_weather_observation(db: Session, location_id: int, weather: dict[str, Any]):
    if not weather.get("time"):
        return
    existing = db.execute(
        text(
            """
            SELECT id FROM weather_observations
            WHERE location_id = :location_id
              AND recorded_at = :recorded_at
            LIMIT 1
            """
        ),
        {"location_id": location_id, "recorded_at": weather["time"]},
    ).scalar()
    if existing:
        return
    db.execute(
        text(
            """
            INSERT INTO weather_observations
            (location_id, temperature, current_rain_mm, rainfall_1h, rainfall_3h,
             rainfall_6h, rainfall_24h, forecast_rain_6h,
             precipitation_probability_max, soil_moisture_0_7cm, recorded_at)
            VALUES
            (:location_id, :temperature, :current_rain_mm, :rainfall_1h, :rainfall_3h,
             :rainfall_6h, :rainfall_24h, :forecast_rain_6h,
             :precipitation_probability_max, :soil_moisture, :recorded_at)
            """
        ),
        {
            "location_id": location_id,
            "temperature": weather.get("temperature"),
            "current_rain_mm": weather.get("current_rain_mm"),
            "rainfall_1h": weather.get("rainfall_1h"),
            "rainfall_3h": weather.get("rainfall_3h"),
            "rainfall_6h": weather.get("rainfall_6h"),
            "rainfall_24h": weather.get("rainfall_24h"),
            "forecast_rain_6h": weather.get("forecast_rain_6h"),
            "precipitation_probability_max": weather.get("precipitation_probability_max"),
            "soil_moisture": weather.get("soil_moisture_0_7cm"),
            "recorded_at": weather.get("time"),
        },
    )


def save_risk_history(
    db: Session,
    location_id: int,
    weather: dict[str, Any],
    terrain: dict[str, Any],
    risk: dict[str, Any],
    source: str,
):
    recorded_at = weather.get("time")
    if not recorded_at:
        return
    last = db.execute(
        text(
            """
            SELECT risk_score, recorded_at
            FROM risk_history
            WHERE location_id = :location_id
            ORDER BY recorded_at DESC
            LIMIT 1
            """
        ),
        {"location_id": location_id},
    ).fetchone()
    if last:
        previous_time = last[1]
        if previous_time is not None:
            try:
                current_time = datetime.fromisoformat(recorded_at)
                if current_time - previous_time < timedelta(minutes=4):
                    return
            except ValueError:
                pass

    db.execute(
        text(
            """
            INSERT INTO risk_history
            (location_id, rainfall_mm, slope_degree, risk_score, risk_level,
             rainfall_score, slope_score, soil_moisture, forecast_rain_6h, source, recorded_at)
            VALUES
            (:location_id, :rainfall_mm, :slope_degree, :risk_score, :risk_level,
             :rainfall_score, :slope_score, :soil_moisture, :forecast_rain_6h, :source, :recorded_at)
            """
        ),
        {
            "location_id": location_id,
            "rainfall_mm": weather.get("rainfall_24h"),
            "slope_degree": terrain.get("slope_degree"),
            "risk_score": risk.get("risk_score"),
            "risk_level": risk.get("risk_level"),
            "rainfall_score": risk.get("rainfall_score"),
            "slope_score": risk.get("slope_score"),
            "soil_moisture": weather.get("soil_moisture_0_7cm"),
            "forecast_rain_6h": weather.get("forecast_rain_6h"),
            "source": source,
            "recorded_at": recorded_at,
        },
    )


def maybe_create_alert(db: Session, location_id: int, location_name: str, risk: dict[str, Any]):
    level = risk["risk_level"]
    if level not in {"HIGH", "CRITICAL"}:
        return

    recent = db.execute(
        text(
            """
            SELECT id
            FROM alerts
            WHERE location_id = :location_id
              AND status = 'ACTIVE'
              AND created_at >= (CURRENT_TIMESTAMP - INTERVAL '30 minutes')
            LIMIT 1
            """
        ),
        {"location_id": location_id},
    ).scalar()
    if recent:
        return

    message = (
        f"{level} landslide risk signal at {location_name}. "
        "Review live rainfall, terrain and field conditions."
    )
    db.execute(
        text(
            """
            INSERT INTO alerts(location_id, risk_level, message, status)
            VALUES (:location_id, :risk_level, :message, 'ACTIVE')
            """
        ),
        {"location_id": location_id, "risk_level": level, "message": message},
    )


def _build_risk_response(
    location_name: str,
    state: str,
    district: str,
    latitude: float,
    longitude: float,
    weather: dict[str, Any],
    terrain: dict[str, Any],
    risk: dict[str, Any],
    ml: dict[str, Any] | None = None,
    source: str = "live",
) -> dict[str, Any]:
    response = {
        "location": location_name,
        "state": state,
        "district": district,
        "latitude": latitude,
        "longitude": longitude,
        "temperature": weather.get("temperature"),
        "current_rain_mm": weather.get("current_rain_mm"),
        "rainfall_1h": weather.get("rainfall_1h"),
        "rainfall_3h": weather.get("rainfall_3h"),
        "rainfall_6h": weather.get("rainfall_6h"),
        "rainfall_24h": weather.get("rainfall_24h"),
        "forecast_rain_6h": weather.get("forecast_rain_6h"),
        "precipitation_probability_max": weather.get("precipitation_probability_max"),
        "soil_moisture_0_7cm": weather.get("soil_moisture_0_7cm"),
        "elevation_m": terrain.get("elevation_m"),
        "slope_degree": terrain.get("slope_degree"),
        "slope_source": terrain.get("source"),
        "rainfall_score": risk.get("rainfall_score"),
        "slope_score": risk.get("slope_score"),
        "soil_moisture_score": risk.get("soil_moisture_score"),
        "forecast_score": risk.get("forecast_score"),
        "risk_score": risk.get("risk_score"),
        "risk_level": risk.get("risk_level"),
        "risk_method": risk.get("method"),
        "recorded_at": weather.get("time"),
        "source": source,
    }
    if ml is not None:
        response["ml"] = ml
    return response


@app.get("/api/locations")
def get_locations(db: Session = Depends(get_db)):
    locations = db.query(Location).order_by(Location.state, Location.district).all()
    return [
        {
            "id": location.id,
            "state": location.state,
            "district": location.district,
            "location_name": location.location_name,
            "latitude": location.latitude,
            "longitude": location.longitude,
        }
        for location in locations
    ]


@app.get("/api/live-weather/{location_id}")
def get_live_weather_data(location_id: int, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    weather = get_live_weather(location.latitude, location.longitude)
    save_weather_observation(db, location.id, weather)
    db.commit()
    return {
        "location": location.location_name,
        "state": location.state,
        "district": location.district,
        "latitude": location.latitude,
        "longitude": location.longitude,
        **weather,
    }


@app.get("/api/live-risk/{location_id}")
def get_live_risk(location_id: int, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    weather = get_live_weather(location.latitude, location.longitude)
    terrain = get_slope(location.id, db)
    risk = calculate_risk(
        weather["rainfall_1h"],
        weather["rainfall_3h"],
        weather["rainfall_6h"],
        weather["rainfall_24h"],
        terrain["slope_degree"],
        weather.get("soil_moisture_0_7cm"),
        weather.get("forecast_rain_6h"),
    )
    ml = predict_experimental(db, weather["rainfall_24h"], terrain["slope_degree"])
    save_weather_observation(db, location.id, weather)
    save_risk_history(db, location.id, weather, terrain, risk, "location_live")
    maybe_create_alert(db, location.id, location.location_name or "Location", risk)
    db.commit()
    return _build_risk_response(
        location.location_name or "Location",
        location.state,
        location.district,
        location.latitude,
        location.longitude,
        weather,
        terrain,
        risk,
        ml,
        "monitoring_location",
    )


@app.get("/api/live-risk-all")
def get_all_live_risk(db: Session = Depends(get_db)):
    locations = db.query(Location).order_by(Location.state, Location.district).all()
    weather_results = get_live_weather_batch(locations)
    weather_by_location = {item["location_id"]: item for item in weather_results}
    result = []

    for location in locations:
        weather = weather_by_location.get(location.id)
        if not weather:
            result.append({
                "id": location.id,
                "location_name": location.location_name,
                "state": location.state,
                "district": location.district,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "risk_level": "UNKNOWN",
            })
            continue

        stored_terrain = get_slope(location.id, db)
        risk = calculate_risk(
            weather["rainfall_1h"],
            weather["rainfall_3h"],
            weather["rainfall_6h"],
            weather["rainfall_24h"],
            stored_terrain["slope_degree"],
            weather.get("soil_moisture_0_7cm"),
            weather.get("forecast_rain_6h"),
        )
        save_weather_observation(db, location.id, weather)
        save_risk_history(db, location.id, weather, stored_terrain, risk, "batch_live")
        maybe_create_alert(db, location.id, location.location_name or "Location", risk)

        result.append({
            "id": location.id,
            "location_name": location.location_name,
            "state": location.state,
            "district": location.district,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "temperature": weather.get("temperature"),
            "current_rain_mm": weather.get("current_rain_mm"),
            "rainfall_1h": weather.get("rainfall_1h"),
            "rainfall_3h": weather.get("rainfall_3h"),
            "rainfall_6h": weather.get("rainfall_6h"),
            "rainfall_24h": weather.get("rainfall_24h"),
            "forecast_rain_6h": weather.get("forecast_rain_6h"),
            "precipitation_probability_max": weather.get("precipitation_probability_max"),
            "soil_moisture_0_7cm": weather.get("soil_moisture_0_7cm"),
            "elevation_m": stored_terrain.get("elevation_m"),
            "slope_degree": stored_terrain.get("slope_degree"),
            "slope_source": stored_terrain.get("source"),
            "rainfall_score": risk.get("rainfall_score"),
            "slope_score": risk.get("slope_score"),
            "soil_moisture_score": risk.get("soil_moisture_score"),
            "forecast_score": risk.get("forecast_score"),
            "risk_score": risk.get("risk_score"),
            "risk_level": risk.get("risk_level"),
            "recorded_at": weather.get("time"),
        })

    db.commit()
    return result


@app.get("/api/risk-by-coordinates")
def risk_by_coordinates(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db),
):
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    weather = get_live_weather(latitude, longitude)
    terrain = get_terrain_profile(latitude, longitude)
    risk = calculate_risk(
        weather["rainfall_1h"],
        weather["rainfall_3h"],
        weather["rainfall_6h"],
        weather["rainfall_24h"],
        terrain["slope_degree"],
        weather.get("soil_moisture_0_7cm"),
        weather.get("forecast_rain_6h"),
    )
    return _build_risk_response(
        "Selected Location",
        "",
        "",
        latitude,
        longitude,
        weather,
        terrain,
        risk,
        None,
        "selected_coordinates",
    )


@app.get("/api/elevation")
def elevation_and_slope(latitude: float, longitude: float):
    return get_terrain_profile(latitude, longitude)


@app.post("/api/terrain/refresh-all")
def refresh_all_terrain(db: Session = Depends(get_db)):
    locations = db.query(Location).order_by(Location.id).all()
    profiles = get_terrain_profiles_batch(locations)
    for profile in profiles:
        db.execute(
            text(
                """
                INSERT INTO slope_data(location_id, elevation_m, slope_degree, source)
                VALUES (:location_id, :elevation_m, :slope_degree, :source)
                """
            ),
            profile,
        )
    db.commit()
    return {
        "updated": len(profiles),
        "source": "Open-Meteo Elevation / Copernicus DEM GLO-90",
        "note": "Approximate cross-neighborhood slope derived from DEM elevations.",
    }


@app.get("/api/risk-history/{location_id}")
def get_risk_history(
    location_id: int,
    limit: int = Query(48, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            """
            SELECT recorded_at, risk_score, risk_level, rainfall_mm,
                   slope_degree, rainfall_score, slope_score,
                   soil_moisture, forecast_rain_6h, source
            FROM risk_history
            WHERE location_id = :location_id
            ORDER BY recorded_at DESC
            LIMIT :limit
            """
        ),
        {"location_id": location_id, "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


@app.get("/api/alerts")
def get_alerts(
    status: str = Query("ACTIVE", pattern="^(ACTIVE|ACKNOWLEDGED|ALL)$"),
    db: Session = Depends(get_db),
):
    if status == "ALL":
        rows = db.execute(
            text(
                """
                SELECT a.id, a.location_id, l.location_name, l.state, l.district,
                       a.risk_level, a.message, a.status, a.created_at, a.acknowledged_at
                FROM alerts a
                LEFT JOIN locations l ON l.id = a.location_id
                ORDER BY a.created_at DESC
                LIMIT 100
                """
            )
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                """
                SELECT a.id, a.location_id, l.location_name, l.state, l.district,
                       a.risk_level, a.message, a.status, a.created_at, a.acknowledged_at
                FROM alerts a
                LEFT JOIN locations l ON l.id = a.location_id
                WHERE a.status = :status
                ORDER BY a.created_at DESC
                LIMIT 100
                """
            ),
            {"status": status},
        ).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text(
            """
            UPDATE alerts
            SET status = 'ACKNOWLEDGED', acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = :alert_id AND status = 'ACTIVE'
            """
        ),
        {"alert_id": alert_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Active alert not found")
    return {"status": "acknowledged", "alert_id": alert_id}


@app.get("/api/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT risk_level, COUNT(*) AS count
            FROM (
                SELECT DISTINCT ON (location_id) location_id, risk_level, recorded_at
                FROM risk_history
                WHERE risk_level IS NOT NULL
                ORDER BY location_id, recorded_at DESC
            ) latest
            GROUP BY risk_level
            """
        )
    ).mappings().all()
    counts = {row["risk_level"]: int(row["count"]) for row in rows}
    total = sum(counts.values())
    return {
        "total_locations_with_history": total,
        "low": counts.get("LOW", 0),
        "medium": counts.get("MEDIUM", 0),
        "high": counts.get("HIGH", 0),
        "critical": counts.get("CRITICAL", 0),
        "active_alerts": int(
            db.execute(text("SELECT COUNT(*) FROM alerts WHERE status = 'ACTIVE'")).scalar() or 0
        ),
    }


@app.get("/api/analytics/trend")
def analytics_trend(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            """
            SELECT
                date_trunc('hour', recorded_at) AS hour,
                ROUND(AVG(risk_score), 2) AS avg_risk_score,
                MAX(risk_score) AS max_risk_score
            FROM risk_history
            WHERE recorded_at >= CURRENT_TIMESTAMP - (:hours * INTERVAL '1 hour')
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {"hours": hours},
    ).mappings().all()
    return [dict(row) for row in rows]


@app.get("/api/analytics/state-summary")
def analytics_state_summary(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (rh.location_id)
                    rh.location_id, rh.risk_score, rh.risk_level, l.state
                FROM risk_history rh
                JOIN locations l ON l.id = rh.location_id
                ORDER BY rh.location_id, rh.recorded_at DESC
            )
            SELECT state,
                   COUNT(*) AS locations,
                   ROUND(AVG(risk_score), 1) AS avg_risk_score,
                   COUNT(*) FILTER (WHERE risk_level IN ('HIGH','CRITICAL')) AS high_or_critical
            FROM latest
            GROUP BY state
            ORDER BY state
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


@app.get("/api/ml/status")
def ml_status(db: Session = Depends(get_db)):
    return get_model_status(db)


@app.post("/api/ml/train")
def ml_train(db: Session = Depends(get_db)):
    try:
        return train_model(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/ml/evaluation")
def ml_evaluation(db: Session = Depends(get_db)):
    row = db.execute(
        text(
            """
            SELECT model_name, model_version, samples, accuracy,
                   precision_score, recall, f1, roc_auc, trained_at
            FROM model_runs
            ORDER BY trained_at DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    return dict(row) if row else {"available": False}


@app.get("/api/satellite/layer")
def satellite_layer():
    return satellite_layer_config()
