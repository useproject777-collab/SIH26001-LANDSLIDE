from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from database import SessionLocal, initialize_database
from sqlalchemy import text

LOCATIONS = [
    ("Sikkim", "Gangtok", "Gangtok Monitoring Point", 27.3389, 88.6065, 38),
    ("Sikkim", "Namchi", "Namchi Monitoring Point", 27.1640, 88.3639, 38),
    ("Sikkim", "Mangan", "Mangan Monitoring Point", 27.5096, 88.5354, 38),
    ("Sikkim", "Gyalshing", "Gyalshing Monitoring Point", 27.2896, 88.2644, 38),
    ("Sikkim", "Pakyong", "Pakyong Monitoring Point", 27.2300, 88.6120, 38),
    ("Arunachal Pradesh", "Tawang", "Tawang Monitoring Point", 27.5860, 91.8590, 42),
    ("Arunachal Pradesh", "Bomdila", "Bomdila Monitoring Point", 27.2647, 92.4247, 42),
    ("Arunachal Pradesh", "Itanagar", "Itanagar Monitoring Point", 27.0844, 93.6053, 42),
    ("Arunachal Pradesh", "Ziro", "Ziro Monitoring Point", 27.5444, 93.8196, 42),
    ("Arunachal Pradesh", "Pasighat", "Pasighat Monitoring Point", 28.0660, 95.3268, 42),
    ("Arunachal Pradesh", "Along", "Along Monitoring Point", 28.1712, 94.7776, 42),
    ("Assam", "Guwahati", "Guwahati Monitoring Point", 26.1445, 91.7362, 18),
    ("Assam", "Dibrugarh", "Dibrugarh Monitoring Point", 27.4728, 94.9120, 18),
    ("Assam", "Silchar", "Silchar Monitoring Point", 24.8333, 92.7789, 18),
    ("Assam", "Jorhat", "Jorhat Monitoring Point", 26.7509, 94.2037, 18),
    ("Assam", "Tezpur", "Tezpur Monitoring Point", 26.6528, 92.7926, 18),
    ("Assam", "Diphu", "Diphu Monitoring Point", 25.8430, 93.4310, 18),
    ("Meghalaya", "Shillong", "Shillong Monitoring Point", 25.5788, 91.8933, 35),
    ("Meghalaya", "Cherrapunji", "Cherrapunji Monitoring Point", 25.2841, 91.7210, 35),
    ("Meghalaya", "Tura", "Tura Monitoring Point", 25.5141, 90.2029, 35),
    ("Meghalaya", "Jowai", "Jowai Monitoring Point", 25.4500, 92.2000, 35),
    ("Meghalaya", "Nongpoh", "Nongpoh Monitoring Point", 25.9000, 91.8833, 35),
    ("Nagaland", "Kohima", "Kohima Monitoring Point", 25.6751, 94.1086, 32),
    ("Nagaland", "Dimapur", "Dimapur Monitoring Point", 25.9117, 93.7217, 32),
    ("Nagaland", "Mokokchung", "Mokokchung Monitoring Point", 26.3220, 94.5180, 32),
    ("Nagaland", "Mon", "Mon Monitoring Point", 26.7167, 95.0333, 32),
    ("Nagaland", "Wokha", "Wokha Monitoring Point", 26.1000, 94.2667, 32),
    ("Manipur", "Imphal", "Imphal Monitoring Point", 24.8170, 93.9368, 30),
    ("Manipur", "Churachandpur", "Churachandpur Monitoring Point", 24.3333, 93.6833, 30),
    ("Manipur", "Ukhrul", "Ukhrul Monitoring Point", 25.0964, 94.3614, 30),
    ("Manipur", "Senapati", "Senapati Monitoring Point", 25.2670, 94.0170, 30),
    ("Mizoram", "Aizawl", "Aizawl Monitoring Point", 23.7271, 92.7176, 40),
    ("Mizoram", "Lunglei", "Lunglei Monitoring Point", 22.8833, 92.7333, 40),
    ("Mizoram", "Champhai", "Champhai Monitoring Point", 23.4667, 93.3167, 40),
    ("Mizoram", "Kolasib", "Kolasib Monitoring Point", 24.2167, 92.6833, 40),
    ("Mizoram", "Serchhip", "Serchhip Monitoring Point", 23.3000, 92.8500, 40),
    ("Tripura", "Agartala", "Agartala Monitoring Point", 23.8315, 91.2868, 22),
    ("Tripura", "Dharmanagar", "Dharmanagar Monitoring Point", 24.3667, 92.1667, 22),
    ("Tripura", "Kailashahar", "Kailashahar Monitoring Point", 24.3333, 92.0167, 22),
    ("Tripura", "Udaipur", "Udaipur Monitoring Point", 23.5333, 91.4833, 22),
    ("Tripura", "Ambassa", "Ambassa Monitoring Point", 23.9333, 91.8500, 22),
    ("Sikkim", "Ravangla", "Ravangla Monitoring Point", 27.3120, 88.3630, 40),
    ("Sikkim", "Soreng", "Soreng Monitoring Point", 27.1700, 88.1900, 38),
    ("Sikkim", "Lachen", "Lachen Monitoring Point", 27.7150, 88.7350, 45),
    ("Arunachal Pradesh", "Bomdila", "Bomdila North Monitoring Point", 27.2700, 92.4200, 45),
    ("Arunachal Pradesh", "Dirang", "Dirang Monitoring Point", 27.3630, 92.2400, 45),
    ("Arunachal Pradesh", "Seppa", "Seppa Monitoring Point", 27.3650, 93.0500, 40),
    ("Arunachal Pradesh", "Daporijo", "Daporijo Monitoring Point", 27.9850, 94.2200, 42),
    ("Arunachal Pradesh", "Tezu", "Tezu Monitoring Point", 27.9120, 96.1280, 38),
    ("Assam", "Haflong", "Haflong Monitoring Point", 25.1667, 93.0167, 35),
    ("Assam", "Diphupar", "Diphupar Monitoring Point", 25.8500, 93.7500, 28),
    ("Assam", "Karbi Anglong", "Karbi Anglong Monitoring Point", 26.0000, 93.4300, 32),
    ("Meghalaya", "Mawsynram", "Mawsynram Monitoring Point", 25.2970, 91.5820, 38),
    ("Meghalaya", "Nongstoin", "Nongstoin Monitoring Point", 25.5200, 91.2700, 38),
    ("Meghalaya", "Williamnagar", "Williamnagar Monitoring Point", 25.4900, 90.6100, 30),
    ("Meghalaya", "Resubelpara", "Resubelpara Monitoring Point", 25.9000, 90.8300, 32),
    ("Nagaland", "Tuensang", "Tuensang Monitoring Point", 26.2700, 94.8300, 38),
    ("Nagaland", "Phek", "Phek Monitoring Point", 25.6700, 94.5200, 36),
    ("Nagaland", "Zunheboto", "Zunheboto Monitoring Point", 26.0100, 94.5200, 34),
    ("Nagaland", "Kiphire", "Kiphire Monitoring Point", 25.8700, 94.7800, 38),
    ("Manipur", "Tamenglong", "Tamenglong Monitoring Point", 24.9800, 93.5000, 42),
    ("Manipur", "Chandel", "Chandel Monitoring Point", 24.3200, 94.0100, 34),
    ("Manipur", "Jiribam", "Jiribam Monitoring Point", 24.8000, 93.1200, 28),
    ("Mizoram", "Mamit", "Mamit Monitoring Point", 23.9300, 92.4900, 38),
    ("Mizoram", "Lawngtlai", "Lawngtlai Monitoring Point", 22.5300, 92.8900, 42),
    ("Mizoram", "Saitual", "Saitual Monitoring Point", 23.9700, 92.5800, 40),
    ("Tripura", "Sabroom", "Sabroom Monitoring Point", 23.0000, 91.7200, 28),
    ("Tripura", "Khowai", "Khowai Monitoring Point", 24.0800, 91.6000, 25),
    ("Tripura", "Teliamura", "Teliamura Monitoring Point", 24.1200, 91.5100, 28),
    ("Tripura", "Belonia", "Belonia Monitoring Point", 23.2500, 91.4500, 25),
]


def main():
    initialize_database()
    db = SessionLocal()
    try:
        inserted = 0
        for state, district, name, lat, lon, demo_slope in LOCATIONS:
            existing = db.execute(
                text(
                    """
                    SELECT id FROM locations
                    WHERE state = :state AND district = :district
                      AND latitude = :latitude AND longitude = :longitude
                    LIMIT 1
                    """
                ),
                {"state": state, "district": district, "latitude": lat, "longitude": lon},
            ).scalar()
            if existing:
                continue
            location_id = db.execute(
                text(
                    """
                    INSERT INTO locations
                    (state, district, location_name, latitude, longitude, geom)
                    VALUES
                    (:state, :district, :name, :latitude, :longitude,
                     ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography)
                    RETURNING id
                    """
                ),
                {
                    "state": state,
                    "district": district,
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                },
            ).scalar()
            db.execute(
                text(
                    """
                    INSERT INTO slope_data(location_id, slope_degree, source)
                    VALUES (:location_id, :slope, 'DEMO SEED - replace with terrain refresh')
                    """
                ),
                {"location_id": location_id, "slope": demo_slope},
            )
            inserted += 1
        db.commit()
        print(f"Seed complete. Inserted {inserted} new demo monitoring locations.")
        print("Demo slope values are intentionally marked as demo data.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
