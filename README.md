# SIH26001-LANDSLIDE — NER Landslide Early Warning System

A website-first prototype for near-real-time landslide risk monitoring in the North Eastern Region (NER).

## Modules included

- PostgreSQL + PostGIS database
- NER monitoring location registry
- Open-Meteo live weather and rainfall windows
- Soil-moisture and forecast rainfall context
- DEM/elevation-based terrain profile and approximate slope
- Single-location and batch live risk calculation
- City/place search
- Browser current-location risk calculation
- Map-click coordinate risk calculation
- Risk history persistence
- High/Critical alert persistence + acknowledgement
- Regional risk distribution analytics
- Experimental RandomForest ML training/evaluation pipeline
- NASA GIBS satellite visual context layer
- Professional responsive dashboard
- Automatic 5-minute refresh

## Data / validation notes

Open-Meteo's current public documentation describes the `/v1/forecast` API as supporting multiple coordinates and hourly/current weather variables, and its elevation API provides terrain elevation from the Copernicus DEM GLO-90 at 90 m resolution. The free API is intended for non-commercial use and requires attribution; check current provider terms before deployment beyond prototyping.

The project's risk formula is a configurable prototype index. Its thresholds and weights are **not** presented as scientifically validated landslide trigger thresholds. DEM-derived slope is approximate because it is estimated from a small neighborhood of elevation samples. The optional ML model is marked experimental and is not used as an operational warning signal until sufficient representative labeled data are provided and validated.

## Windows setup

### 1. PostgreSQL/PostGIS

Create the database in pgAdmin Query Tool:

```sql
CREATE DATABASE landslide_db;
```

Then enable PostGIS inside that database:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Backend

Open Command Prompt:

```cmd
cd /d D:\SIH26001-LANDSLIDE\backend
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from the example:

```cmd
copy .env.example .env
```

Edit `.env` and put your PostgreSQL password:

```text
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/landslide_db
```

Initialize schema:

```cmd
python scripts\init_db.py
```

For a fresh demo database, seed the 41 NER prototype monitoring points:

```cmd
cd /d D:\SIH26001-LANDSLIDE
python database\seed_demo_data.py
```

Run backend:

```cmd
cd /d D:\SIH26001-LANDSLIDE\backend
venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Test:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

### 3. Refresh terrain from DEM

After the backend is running, refresh all monitoring-point terrain values:

```text
POST http://127.0.0.1:8000/api/terrain/refresh-all
```

The dashboard also has **Refresh Terrain**.

### 4. Frontend

Open a second Command Prompt:

```cmd
cd /d D:\SIH26001-LANDSLIDE\frontend
npm install
```

Optional:

```cmd
copy .env.example .env
```

Run:

```cmd
npm run dev
```

Open:

```text
http://localhost:5173
```

## Two-terminal workflow

Terminal 1:

```cmd
cd /d D:\SIH26001-LANDSLIDE\backend
venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```cmd
cd /d D:\SIH26001-LANDSLIDE\frontend
npm run dev
```

PostgreSQL service must also be running.

## ML module

The ML pipeline uses records from `historical_landslides`.

Check readiness:

```text
GET http://127.0.0.1:8000/api/ml/status
```

Train only after you have sufficient representative labeled data:

```cmd
cd /d D:\SIH26001-LANDSLIDE\backend
venv\Scripts\activate
python scripts\train_model.py
```

or use the dashboard button.

The included project does **not** seed fake historical landslide labels by default.

## Important

Never put the real PostgreSQL password in GitHub. Keep `backend/.env` local and commit only `.env.example`.
