from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from database import initialize_database


if __name__ == "__main__":
    initialize_database()
    print("Database schema initialized successfully.")
