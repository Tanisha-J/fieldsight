# backend/app/services/telemetry_service.py
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

# insert telemetry data into table and saves it
def store_telemetry(
    db: Session,
    rover_id: int,
    battery: float,
    gps_lat: float,
    gps_lng: float,
    heading: float | None,
    captured_at: datetime | None = None,
) -> None:
    
    ts = captured_at or datetime.now(timezone.utc) # either uses determined time stamp or UTC time

    # uses INSERT to put new row into telemetry table
    db.execute(
        text(
            """
            INSERT INTO Telemetry (rover_id, battery, gps_lat, gps_lng, heading, captured_at)
            VALUES (:rover_id, :battery, :gps_lat, :gps_lng, :heading, :captured_at)
            """
        ),
        {
            "rover_id": rover_id,
            "battery": battery,
            "gps_lat": gps_lat,
            "gps_lng": gps_lng,
            "heading": heading,
            "captured_at": ts,
        },
    )
    
    # permanently saves row into table
    db.commit()

# returns latest telemetry row in table
def get_latest_telemetry(db: Session, rover_id: int):

    # takes current database session, and then we execute the raw sql query, convert result into dict mapping, and then take first row 
    row = db.execute(
        text(
            # we are selecting specific columns from the telemetry table, only from rows of rover_id, and then sorting
            # from newest to oldest, and taking only the first row 
            """
            SELECT rover_id, battery, gps_lat, gps_lng, heading, captured_at 
            FROM Telemetry
            WHERE rover_id = :rover_id
            ORDER BY captured_at DESC
            LIMIT 1
            """
        ),
        {
            "rover_id": rover_id
        },
    ).mappings().first()

    # sends back dict only if there is a row 
    return dict(row) if row else None
