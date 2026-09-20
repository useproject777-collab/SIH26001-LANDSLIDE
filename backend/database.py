import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Copy .env.example to .env and set the PostgreSQL password."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    """Create/upgrade the tables used by the app without deleting user data."""
    ddl = [
        "CREATE EXTENSION IF NOT EXISTS postgis",
        """
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            state VARCHAR(100) NOT NULL,
            district VARCHAR(100) NOT NULL,
            location_name VARCHAR(200),
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            geom GEOGRAPHY(POINT, 4326),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS rainfall (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            rainfall_mm DOUBLE PRECISION NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS landslides (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            severity VARCHAR(50),
            cause VARCHAR(200),
            description TEXT,
            occurred_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS risk_predictions (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            risk_score DOUBLE PRECISION NOT NULL,
            risk_level VARCHAR(50) NOT NULL,
            predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS slope_data (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            elevation_m DOUBLE PRECISION,
            slope_degree DOUBLE PRECISION NOT NULL,
            source VARCHAR(200),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS historical_landslides (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            rainfall_mm DOUBLE PRECISION NOT NULL,
            slope_degree DOUBLE PRECISION NOT NULL,
            landslide_occurred BOOLEAN NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS risk_history (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            rainfall_mm DOUBLE PRECISION,
            slope_degree DOUBLE PRECISION,
            risk_score INTEGER,
            risk_level VARCHAR(20),
            rainfall_score INTEGER,
            slope_score INTEGER,
            soil_moisture DOUBLE PRECISION,
            forecast_rain_6h DOUBLE PRECISION,
            source VARCHAR(100),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS weather_observations (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            temperature DOUBLE PRECISION,
            current_rain_mm DOUBLE PRECISION,
            rainfall_1h DOUBLE PRECISION,
            rainfall_3h DOUBLE PRECISION,
            rainfall_6h DOUBLE PRECISION,
            rainfall_24h DOUBLE PRECISION,
            forecast_rain_6h DOUBLE PRECISION,
            precipitation_probability_max DOUBLE PRECISION,
            soil_moisture_0_7cm DOUBLE PRECISION,
            recorded_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            risk_level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acknowledged_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS model_runs (
            id SERIAL PRIMARY KEY,
            model_name VARCHAR(100) NOT NULL,
            model_version VARCHAR(50),
            samples INTEGER,
            accuracy DOUBLE PRECISION,
            precision_score DOUBLE PRECISION,
            recall DOUBLE PRECISION,
            f1 DOUBLE PRECISION,
            roc_auc DOUBLE PRECISION,
            trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            artifact_path VARCHAR(400)
        )
        """,
        "ALTER TABLE slope_data ADD COLUMN IF NOT EXISTS elevation_m DOUBLE PRECISION",
        "ALTER TABLE slope_data ADD COLUMN IF NOT EXISTS source VARCHAR(200)",
        "ALTER TABLE risk_history ADD COLUMN IF NOT EXISTS rainfall_score INTEGER",
        "ALTER TABLE risk_history ADD COLUMN IF NOT EXISTS slope_score INTEGER",
        "ALTER TABLE risk_history ADD COLUMN IF NOT EXISTS soil_moisture DOUBLE PRECISION",
        "ALTER TABLE risk_history ADD COLUMN IF NOT EXISTS forecast_rain_6h DOUBLE PRECISION",
        "ALTER TABLE risk_history ADD COLUMN IF NOT EXISTS source VARCHAR(100)",
        "ALTER TABLE historical_landslides ADD COLUMN IF NOT EXISTS source VARCHAR(100)",
        """
        UPDATE locations
        SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
        WHERE geom IS NULL
        """,
        "CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING GIST (geom)",
        "CREATE INDEX IF NOT EXISTS idx_risk_history_location_time ON risk_history(location_id, recorded_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_weather_location_time ON weather_observations(location_id, recorded_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_status_time ON alerts(status, created_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS citizen_reports (
            id SERIAL PRIMARY KEY,
            reporter_name VARCHAR(120),
            report_type VARCHAR(40) NOT NULL DEFAULT 'OBSERVATION',
            description TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            location_name VARCHAR(200),
            media_data BYTEA,
            media_content_type VARCHAR(100),
            media_filename VARCHAR(255),
            status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS road_reports (
            id SERIAL PRIMARY KEY,
            road_name VARCHAR(250) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
            description TEXT,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            reported_by VARCHAR(120),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sensor_observations (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id),
            sensor_id VARCHAR(100) NOT NULL,
            soil_moisture DOUBLE PRECISION,
            vibration DOUBLE PRECISION,
            battery_percent DOUBLE PRECISION,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_citizen_reports_time ON citizen_reports(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_road_reports_time ON road_reports(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sensor_location_time ON sensor_observations(location_id, recorded_at DESC)",
        """CREATE TABLE IF NOT EXISTS app_users (id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL, email VARCHAR(320) UNIQUE NOT NULL, phone VARCHAR(30), aadhaar_hash VARCHAR(64), email_verified BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS email_otps (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES app_users(id) ON DELETE CASCADE, purpose VARCHAR(30) NOT NULL, otp_hash VARCHAR(64) NOT NULL, expires_at TIMESTAMP NOT NULL, used BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES app_users(id)""",
        """CREATE TABLE IF NOT EXISTS warning_email_log (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES app_users(id) ON DELETE CASCADE, risk_level VARCHAR(20) NOT NULL, location_name VARCHAR(200), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        "CREATE INDEX IF NOT EXISTS idx_warning_email_user_time ON warning_email_log(user_id, created_at DESC)",
    ]

    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))
