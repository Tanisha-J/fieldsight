from sqlalchemy import Column, Integer, BigInteger, String, Enum, TIMESTAMP, Double, Boolean, ForeignKey, DATE, Index
from sqlalchemy.sql import func
from app.db import Base


class Farmer(Base):
    __tablename__ = "Farmers"

    farmer_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    username = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    last_login = Column(TIMESTAMP, nullable=True)
    farm_name = Column(String(50), nullable=False)


class RoverSession(Base):
    __tablename__ = "Rover_Sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(Integer, ForeignKey("Farmers.farmer_id"), nullable=False)
    session_date = Column(DATE, nullable=False)
    started_at = Column(TIMESTAMP, nullable=True)
    stopped_at = Column(TIMESTAMP, nullable=True)
    status = Column(Enum("Running", "Stopped", "Processing", "Completed"), default="Stopped", nullable=False)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    active_command = Column(Enum("idle", "stop", "start"), default="idle", nullable=False)


class Scan(Base):
    __tablename__ = "Scans"

    scan_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("Rover_Sessions.session_id"), nullable=True)
    farmer_id = Column(Integer, ForeignKey("Farmers.farmer_id"), nullable=False)
    disease_status = Column(Enum("DISEASED", "HEALTHY", "NO PLANT"), nullable=False)
    image_url = Column(String(255), nullable=False)
    image_key = Column(String(255), nullable=False)
    severity = Column(Enum("YELLOW", "RED", "ORANGE"), nullable=False)
    gemini_status = Column(String(20), nullable=True)
    scanned_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    gps_lat = Column(Double, nullable=False)
    gps_lng = Column(Double, nullable=False)


class Telemetry(Base):
    __tablename__ = "Telemetry"

    telemetry_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("Rover_Sessions.session_id"), nullable=False)
    rover_id = Column(Integer, nullable=False)
    battery = Column(Double, nullable=False)
    gps_lat = Column(Double, nullable=False)
    gps_lng = Column(Double, nullable=False)
    heading = Column(Double, nullable=True)
    captured_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_telemetry_session_time", "session_id", "captured_at"),
        Index("idx_telemetry_rover_time", "rover_id", "captured_at"),
    )
