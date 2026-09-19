from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from database import SessionLocal, initialize_database
from models import Location
from terrain import get_terrain_profiles_batch
from sqlalchemy import text

if __name__ == "__main__":
    initialize_database()
    db = SessionLocal()
    try:
        locations = db.query(Location).order_by(Location.id).all()
        profiles = get_terrain_profiles_batch(locations)
        for profile in profiles:
            db.execute(text("""
                INSERT INTO slope_data(location_id, elevation_m, slope_degree, source)
                VALUES (:location_id, :elevation_m, :slope_degree, :source)
            """), profile)
        db.commit()
        print(f"Terrain refreshed for {len(profiles)} locations.")
    finally:
        db.close()
