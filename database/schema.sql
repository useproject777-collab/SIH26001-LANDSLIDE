CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    location_name VARCHAR(200),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOGRAPHY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rainfall (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    rainfall_mm DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS landslides (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    severity VARCHAR(50),
    cause VARCHAR(200),
    description TEXT,
    occurred_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_predictions (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    risk_score DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS slope_data (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    elevation_m DOUBLE PRECISION,
    slope_degree DOUBLE PRECISION NOT NULL,
    source VARCHAR(200),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historical_landslides (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    rainfall_mm DOUBLE PRECISION NOT NULL,
    slope_degree DOUBLE PRECISION NOT NULL,
    landslide_occurred BOOLEAN NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(100)
);

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
);

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
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    risk_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP
);

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
);
