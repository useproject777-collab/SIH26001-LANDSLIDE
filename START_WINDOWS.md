# Quick Start (Windows)

## Terminal 0 — PostgreSQL
Make sure the PostgreSQL 18 service is running and pgAdmin can connect.

Create the database once:

```sql
CREATE DATABASE landslide_db;
```

## Terminal 1 — Backend

```cmd
cd /d D:\SIH26001-LANDSLIDE\backend
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend\.env` and set your PostgreSQL password.

Then:

```cmd
python scripts\init_db.py
cd ..
python database\seed_demo_data.py
cd backend
venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Terminal 2 — Frontend

```cmd
cd /d D:\SIH26001-LANDSLIDE\frontend
npm install
copy .env.example .env
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## First demo checks

1. Open the website and confirm `LIVE` status.
2. Search `Cherrapunji` or `Gangtok`.
3. Click a colored monitoring marker.
4. Click open map space to calculate a coordinate-based risk.
5. Click `Use My Location` and allow browser location access.
6. Click `Satellite` to view the NASA GIBS visual layer.
7. Click `Refresh Terrain` to replace demo slope values with DEM-derived terrain profiles.

The project intentionally does not ship `node_modules` or the Python virtual environment. `npm install` and `pip install -r requirements.txt` are required once on the target Windows machine.
