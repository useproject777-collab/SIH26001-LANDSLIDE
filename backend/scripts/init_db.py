from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from database import initialize_database
if __name__ == "__main__":
    initialize_database()
    print("Database schema initialized successfully.")
