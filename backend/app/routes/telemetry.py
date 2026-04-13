# backend/app/routes/telemetry.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.telemetry_service import get_latest_telemetry

# defining file path
router = APIRouter(prefix="/rover", tags=["telemetry"])

# registering HTTP get end point for a specific rover ID
@router.get("/telemetry/latest/{rover_id}")
def latest_telemetry(rover_id: int, db: Session = Depends(get_db)): # function handles sending telemetry data to frontend and possible errors
    try:
        row = get_latest_telemetry(db=db, rover_id=rover_id) # calls on telemetry_service.py function to fetch row from database
        if not row: 
            raise HTTPException(status_code=404, detail="No telemetry data found for the rover.") # exception occurs if no row is returned
        return row
    except HTTPException: 
        raise   # continue with current 404 error
    except Exception as e:  # catch any other exceptions 
        raise HTTPException(status_code=500, detail=f"Failed to fetch telemetry data: {e}")