from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, initialize_database
from models import Location
from risk import calculate_risk
from terrain import get_terrain_profile, get_terrain_profiles_batch
from weather import get_live_weather, get_live_weather_batch
from ml_service import get_model_status, predict_experimental, train_model
from satellite import satellite_layer_config
from auth import hash_value, make_token, read_token, generate_otp, otp_expiry, send_email
import os
def current_auth(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return read_token(authorization[7:])

def require_user(authorization: str | None = Header(default=None)):
    auth = current_auth(authorization)
    if not auth or auth.get("role") not in {"user", "admin"}:
        raise HTTPException(status_code=401, detail="Login required")
    return auth

def require_admin(authorization: str | None = Header(default=None)):
    auth = current_auth(authorization)
    if not auth or auth.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return auth


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


def maybe_send_user_warning(db: Session, auth, location_name: str, risk: dict[str, Any]):
    if not auth or auth.get("role") != "user" or risk.get("risk_level") not in {"HIGH", "CRITICAL"}:
        return {"email_warning": False, "reason": "not_required"}
    recent = db.execute(text("SELECT id FROM warning_email_log WHERE user_id=:uid AND risk_level=:level AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 minutes' LIMIT 1"), {"uid": auth["user_id"], "level": risk["risk_level"]}).scalar()
    if recent:
        return {"email_warning": False, "reason": "already_sent_recently"}
    try:
        send_email(auth["email"], f"{risk['risk_level']} Landslide Warning - NER", f"Warning: the current prototype risk engine has identified {risk['risk_level']} risk at {location_name}.\n\nRisk score: {risk.get('risk_score')}/100\nRainfall score: {risk.get('rainfall_score')}/100\nSlope score: {risk.get('slope_score')}/100\n\nPlease follow local disaster-management instructions. This system is an early-warning prototype and does not replace official advisories.")
        db.execute(text("INSERT INTO warning_email_log(user_id,risk_level,location_name) VALUES(:uid,:level,:name)"), {"uid": auth["user_id"], "level": risk["risk_level"], "name": location_name[:200]})
        db.commit()
        return {"email_warning": True, "reason": "sent"}
    except RuntimeError:
        return {"email_warning": False, "reason": "smtp_not_configured"}

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


@app.post("/api/auth/register")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    aadhaar: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    aadhaar = ''.join(ch for ch in aadhaar if ch.isdigit())
    if len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar must contain 12 digits. Only a checksum/format check is performed; UIDAI identity authentication is not available in this free prototype.")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    user = db.execute(text("SELECT id FROM app_users WHERE email=:email"), {"email": email}).scalar()
    if user:
        user_id = user
        db.execute(text("UPDATE app_users SET name=:name, phone=:phone, aadhaar_hash=:aadhaar_hash, email_verified=FALSE, updated_at=CURRENT_TIMESTAMP WHERE id=:id"), {"name": name[:120], "phone": phone[:30], "aadhaar_hash": hash_value(aadhaar), "id": user_id})
    else:
        user_id = db.execute(text("""INSERT INTO app_users(name,email,phone,aadhaar_hash) VALUES(:name,:email,:phone,:aadhaar_hash) RETURNING id"""), {"name": name[:120], "email": email, "phone": phone[:30], "aadhaar_hash": hash_value(aadhaar)}).scalar()
    db.execute(text("UPDATE email_otps SET used=TRUE WHERE user_id=:id AND purpose='verify' AND used=FALSE"), {"id": user_id})
    otp = generate_otp()
    db.execute(text("INSERT INTO email_otps(user_id,purpose,otp_hash,expires_at) VALUES(:uid,'verify',:otp,:expires)"), {"uid": user_id, "otp": hash_value(otp), "expires": otp_expiry()})
    db.commit()
    try:
        result = send_email(email, "NER Landslide Alert System - Email Verification", f"Your verification code is valid for 10 minutes.\n\nVerification code: {otp}\n\nUse this code to verify your email.")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "Unable to send the verification email."))
    response = {"status": "verification_sent", "email": email}
    if result.get("dev_code"):
        response["dev_code"] = result["dev_code"]
    return response

@app.post("/api/auth/verify-email")
def verify_email(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    row = db.execute(text("""SELECT u.id, u.email, o.id AS otp_id, o.otp_hash, o.expires_at FROM app_users u JOIN email_otps o ON o.user_id=u.id WHERE u.email=:email AND o.purpose='verify' AND o.used=FALSE ORDER BY o.created_at DESC LIMIT 1"""), {"email": email}).mappings().first()
    if not row or _otp_expired(row["expires_at"]):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")
    if not hmac_compare(hash_value(otp), row["otp_hash"]):
        raise HTTPException(status_code=400, detail="Invalid verification code.")
    db.execute(text("UPDATE app_users SET email_verified=TRUE, updated_at=CURRENT_TIMESTAMP WHERE id=:id"), {"id": row["id"]})
    db.execute(text("UPDATE email_otps SET used=TRUE WHERE id=:id"), {"id": row["otp_id"]})
    db.commit()
    return {"token": make_token(row["id"], "user", email), "role": "user", "user_id": row["id"],
            "name": db.execute(text("SELECT name FROM app_users WHERE id=:id"), {"id": row["id"]}).scalar(),
            "email": email}

def _otp_expired(value) -> bool:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return True
    if value is None:
        return True
    if getattr(value, "tzinfo", None) is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value < datetime.now(timezone.utc).replace(tzinfo=None)


def hmac_compare(a: str, b: str):
    import hmac
    return hmac.compare_digest(a, b)

@app.post("/api/auth/request-login-otp")
def request_login_otp(email: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    row = db.execute(text("SELECT id, email_verified FROM app_users WHERE email=:email"), {"email": email}).mappings().first()
    if not row or not row["email_verified"]:
        raise HTTPException(status_code=400, detail="Email is not registered/verified. Please register first.")
    db.execute(text("UPDATE email_otps SET used=TRUE WHERE user_id=:id AND purpose='login' AND used=FALSE"), {"id": row["id"]})
    otp = generate_otp()
    db.execute(text("INSERT INTO email_otps(user_id,purpose,otp_hash,expires_at) VALUES(:uid,'login',:otp,:expires)"), {"uid": row["id"], "otp": hash_value(otp), "expires": otp_expiry()})
    db.commit()
    try:
        result = send_email(email, "NER Landslide Alert System - Login Code", f"Your login verification code is valid for 10 minutes.\n\nVerification code: {otp}")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "Unable to send the login email."))
    response={"status":"login_code_sent","email":email}
    if result.get("dev_code"): response["dev_code"]=result["dev_code"]
    return response

@app.post("/api/auth/login-otp")
def login_otp(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    email=email.strip().lower()
    row=db.execute(text("""SELECT u.id,o.id AS otp_id,o.otp_hash,o.expires_at FROM app_users u JOIN email_otps o ON o.user_id=u.id WHERE u.email=:email AND u.email_verified=TRUE AND o.purpose='login' AND o.used=FALSE ORDER BY o.created_at DESC LIMIT 1"""), {"email":email}).mappings().first()
    if not row or _otp_expired(row["expires_at"]) or not hmac_compare(hash_value(otp), row["otp_hash"]):
        raise HTTPException(status_code=400, detail="Invalid or expired login code.")
    db.execute(text("UPDATE email_otps SET used=TRUE WHERE id=:id"), {"id":row["otp_id"]})
    db.commit()
    return {"token": make_token(row["id"], "user", email), "role": "user", "user_id": row["id"],
            "name": db.execute(text("SELECT name FROM app_users WHERE id=:id"), {"id": row["id"]}).scalar(),
            "email": email}

@app.post("/api/auth/admin-login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if username != os.getenv("ADMIN_USERNAME", "admin") or password != os.getenv("ADMIN_PASSWORD", "change-this-admin-password"):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return {"token":make_token(0,"admin",username),"role":"admin","email":username}

@app.get("/api/auth/me")
def auth_me(auth=Depends(require_user), db: Session = Depends(get_db)):
    if auth.get("role") == "admin":
        return auth
    row = db.execute(
        text("SELECT id, name, email, phone, email_verified FROM app_users WHERE id=:id"),
        {"id": auth["user_id"]},
    ).mappings().first()
    if not row or not row["email_verified"]:
        raise HTTPException(status_code=401, detail="User account is not verified")
    return {
        "user_id": row["id"],
        "role": "user",
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "email_verified": row["email_verified"],
    }

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
def get_live_risk(location_id: int, db: Session = Depends(get_db), auth=Depends(require_user)):
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
    email_warning = maybe_send_user_warning(db, auth, location.location_name or "Location", risk)
    db.commit()
    response = _build_risk_response(
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
    response.update(email_warning)
    return response


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
    auth=Depends(require_user),
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
    email_warning = maybe_send_user_warning(db, auth, "Selected Location", risk)
    response = _build_risk_response(
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
    response.update(email_warning)
    return response


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


@app.get("/api/citizen-reports")
def citizen_reports(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), auth=Depends(require_admin)):
    rows = db.execute(text("""
        SELECT id, reporter_name, report_type, description, latitude, longitude,
               location_name, media_content_type, media_filename, status, created_at
        FROM citizen_reports ORDER BY created_at DESC LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/citizen-reports")
async def create_citizen_report(
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    report_type: str = Form("OBSERVATION"),
    reporter_name: str = Form("Citizen"),
    location_name: str = Form(""),
    media: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    auth=Depends(require_user),
):
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    allowed = {"OBSERVATION", "CRACK", "SLOPE_MOVEMENT", "BLOCKED_ROAD", "FLOODING"}
    if report_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid report type")
    media_bytes = None
    media_type = None
    media_name = None
    if media:
        media_bytes = await media.read()
        if len(media_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Media must be 5 MB or smaller")
        media_type = media.content_type or "application/octet-stream"
        media_name = media.filename
    row = db.execute(text("""
        INSERT INTO citizen_reports
        (user_id, reporter_name, report_type, description, latitude, longitude, location_name,
         media_data, media_content_type, media_filename, status)
        VALUES (:user_id, :reporter_name, :report_type, :description, :latitude, :longitude,
                :location_name, :media_data, :media_content_type, :media_filename, 'SUBMITTED')
        RETURNING id, created_at
    """), {
        "user_id": auth["user_id"], "reporter_name": reporter_name[:120], "report_type": report_type,
        "description": description[:5000], "latitude": latitude, "longitude": longitude,
        "location_name": location_name[:200], "media_data": media_bytes,
        "media_content_type": media_type, "media_filename": media_name,
    }).mappings().first()
    db.commit()
    return {"status": "submitted", "id": row["id"], "created_at": row["created_at"]}


@app.get("/api/citizen-reports/{report_id}/media")
def citizen_report_media(report_id: int, db: Session = Depends(get_db), auth=Depends(require_admin)):
    row = db.execute(text("""
        SELECT media_data, media_content_type, media_filename
        FROM citizen_reports WHERE id = :id
    """), {"id": report_id}).mappings().first()
    if not row or row["media_data"] is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return Response(content=bytes(row["media_data"]), media_type=row["media_content_type"] or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{row["media_filename"] or "report-media"}"'})


@app.get("/api/admin/road-reports")
def admin_road_reports(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), auth=Depends(require_admin)):
    rows = db.execute(text("SELECT id, road_name, status, description, latitude, longitude, reported_by, created_at FROM road_reports ORDER BY created_at DESC LIMIT :limit"), {"limit":limit}).mappings().all()
    return [dict(row) for row in rows]

@app.get("/api/road-reports")
def road_reports(status: str = Query("ALL", pattern="^(ALL|OPEN|BLOCKED|RESTRICTED)$"), db: Session = Depends(get_db)):
    where = "" if status == "ALL" else "WHERE status = :status"
    rows = db.execute(text(f"""
        SELECT id, road_name, status, description, latitude, longitude, reported_by, created_at
        FROM road_reports {where} ORDER BY created_at DESC LIMIT 100
    """), ({"status": status} if status != "ALL" else {})).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/road-reports")
def create_road_report(
    road_name: str = Form(...),
    status: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str = Form(""),
    reported_by: str = Form("Field Official"),
    db: Session = Depends(get_db),
):
    if status not in {"OPEN", "BLOCKED", "RESTRICTED"}:
        raise HTTPException(status_code=400, detail="Invalid road status")
    row = db.execute(text("""
        INSERT INTO road_reports(road_name, status, description, latitude, longitude, reported_by)
        VALUES (:road_name, :status, :description, :latitude, :longitude, :reported_by)
        RETURNING id, created_at
    """), {"road_name": road_name[:250], "status": status, "description": description[:2000],
          "latitude": latitude, "longitude": longitude, "reported_by": reported_by[:120]}).mappings().first()
    db.commit()
    return {"status": "saved", "id": row["id"], "created_at": row["created_at"]}


@app.get("/api/admin/reports")
def admin_reports(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), auth=Depends(require_admin)):
    rows = db.execute(text("""SELECT id, user_id, reporter_name, report_type, description, latitude, longitude, location_name, media_content_type, media_filename, status, created_at FROM citizen_reports ORDER BY created_at DESC LIMIT :limit"""), {"limit":limit}).mappings().all()
    return [dict(row) for row in rows]

@app.get("/api/sensors/latest")
def latest_sensors(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT DISTINCT ON (sensor_id) sensor_id, location_id, soil_moisture, vibration,
               battery_percent, recorded_at
        FROM sensor_observations ORDER BY sensor_id, recorded_at DESC
    """)).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/sensors/ingest")
def ingest_sensor(
    sensor_id: str = Form(...),
    location_id: int = Form(...),
    soil_moisture: float | None = Form(None),
    vibration: float | None = Form(None),
    battery_percent: float | None = Form(None),
    db: Session = Depends(get_db),
):
    if not db.query(Location).filter(Location.id == location_id).first():
        raise HTTPException(status_code=404, detail="Location not found")
    db.execute(text("""
        INSERT INTO sensor_observations(sensor_id, location_id, soil_moisture, vibration, battery_percent)
        VALUES (:sensor_id, :location_id, :soil_moisture, :vibration, :battery_percent)
    """), {"sensor_id": sensor_id[:100], "location_id": location_id,
          "soil_moisture": soil_moisture, "vibration": vibration, "battery_percent": battery_percent})
    db.commit()
    return {"status": "accepted", "sensor_id": sensor_id, "location_id": location_id}
