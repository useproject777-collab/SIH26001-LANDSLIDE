from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from .database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    location_name = Column(String(200))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


class HistoricalLandslide(Base):
    __tablename__ = "historical_landslides"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer)
    rainfall_mm = Column(Float, nullable=False)
    slope_degree = Column(Float, nullable=False)
    landslide_occurred = Column(Boolean, nullable=False)
    recorded_at = Column(DateTime)
    source = Column(String(100))


class RiskHistory(Base):
    __tablename__ = "risk_history"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer)
    rainfall_mm = Column(Float)
    slope_degree = Column(Float)
    risk_score = Column(Integer)
    risk_level = Column(String(20))
    rainfall_score = Column(Integer)
    slope_score = Column(Integer)
    soil_moisture = Column(Float)
    forecast_rain_6h = Column(Float)
    source = Column(String(100))
    recorded_at = Column(DateTime)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer)
    risk_level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
