# Database setup

1. PostgreSQL 18 and PostGIS must be installed.
2. Create the database:

```sql
CREATE DATABASE landslide_db;
```

3. The backend automatically creates the required tables on startup. You can also run:

```cmd
cd backend
venv\Scripts\activate
python scripts\init_db.py
```

4. For a fresh demo database, run:

```cmd
python database\seed_demo_data.py
```

The seeded monitoring points and seeded slope values are **demo/prototype data**. Refresh terrain from the backend before treating the terrain values as DEM-derived project outputs.
