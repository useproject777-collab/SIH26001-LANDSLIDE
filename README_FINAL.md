# SIH26001 – NER Landslide Early Warning & Risk Monitoring System

A zero-cost/open-source oriented SIH 26001 software prototype for the North Eastern Region.

## Implemented modules

1. Live rainfall/weather: Open-Meteo current + hourly history + six-hour forecast context.
2. Location intelligence: NER monitoring points, Open-Meteo geocoding, browser location, map-click risk.
3. Coordinate-specific terrain: Open-Meteo elevation with a five-point local DEM slope estimate.
4. Risk engine: rainfall + slope + soil-moisture + forecast context with LOW/MEDIUM/HIGH/CRITICAL levels.
5. GIS dashboard: Leaflet + OpenStreetMap, risk markers, selected-coordinate marker, NASA GIBS satellite visual layer.
6. Early warning: persisted alerts, acknowledgement, browser notifications.
7. Analytics: distribution, state summary, risk history, trend endpoints and CSV export.
8. AI/ML: RandomForest training/evaluation pipeline, experimental probability kept separate from prototype operational score.
9. Citizen/field reporting: geo-tagged observation/crack/slope movement/flooding/blocked-road reports with optional <=5 MB image/video attachment.
10. Road connectivity: OPEN/RESTRICTED/BLOCKED field reports and response-priority context.
11. Sensor integration: REST ingestion for soil moisture, vibration and battery readings; ready for ESP32/Arduino gateways.
12. Multilingual UI selector: English/Tamil/Hindi for the main field-reporting section; architecture can be extended to every label.
13. Low-network PWA shell: manifest + service worker cache for core UI assets. API actions still require connectivity.
14. PostgreSQL/PostGIS schema with persistent observations and indexes.

## Important scientific limitation

The operational risk score is a prototype engineering score, not a validated landslide probability. The slope value is an estimated local gradient derived from nearby DEM elevations. The ML model is explicitly experimental until trained and validated with representative historical landslide labels.

## Local setup – Windows

### Backend

```cmd
cd SIH26001-LANDSLIDE\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
python scripts\init_db.py
uvicorn main:app --reload
```

### Frontend

```cmd
cd SIH26001-LANDSLIDE\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Production / Vercel

The repository keeps the existing Vercel Services architecture: Vite frontend + FastAPI backend under one project with `/api/*` rewrites. Configure `DATABASE_URL` in Vercel and make sure the database has the schema from `database/schema.sql` (or let FastAPI startup create/upgrade its tables). Do not upload local `.env` files or PostgreSQL passwords.

## Free/open-source data and services used

- Open-Meteo weather/elevation/geocoding
- OpenStreetMap map tiles
- Leaflet / React-Leaflet
- NASA GIBS satellite visual layer
- PostgreSQL + PostGIS
- FastAPI
- React + Vite
- scikit-learn / pandas / joblib

## Optional paid production integrations

SMS delivery, large-scale object storage, high-volume satellite processing, and physical sensor hardware may introduce cost. The included prototype does not require them to run its main dashboard.
