from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from database import SessionLocal, initialize_database
from ml_service import train_model


if __name__ == "__main__":
    initialize_database()
    db = SessionLocal()
    try:
        print(train_model(db))
    finally:
        db.close()
