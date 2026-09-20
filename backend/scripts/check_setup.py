from pathlib import Path
import os
import sys
from sqlalchemy import text
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from database import SessionLocal, initialize_database

def main():
    initialize_database()
    db = SessionLocal()
    try:
        print(f"DATABASE_URL: {'OK' if os.getenv('DATABASE_URL') else 'MISSING'}")
        print(f"AUTH_SECRET: {'OK' if os.getenv('AUTH_SECRET') else 'MISSING'}")
        print(f"ADMIN_USERNAME: {'OK' if os.getenv('ADMIN_USERNAME') else 'MISSING'}")
        print(f"ADMIN_PASSWORD: {'OK' if os.getenv('ADMIN_PASSWORD') else 'MISSING'}")
        print(f"DEV_EMAIL_MODE: {os.getenv('DEV_EMAIL_MODE', 'false')}")
        print(f"app_users table: {db.execute(text("SELECT to_regclass('public.app_users')")).scalar()}")
        print(f"email_otps table: {db.execute(text("SELECT to_regclass('public.email_otps')")).scalar()}")
        print(f"locations: {db.execute(text("SELECT COUNT(*) FROM locations")).scalar()}")
        print("Setup check complete.")
    finally:
        db.close()
if __name__ == "__main__": main()
