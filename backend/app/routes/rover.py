from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db import get_db
from app.models import RoverSession
from app.services.rover_service import stop_rover
from app.services.mqtt_service import publish_command

router = APIRouter(prefix="/rover", tags=["rover"])

@router.post("/start")
def start(farmer_id: int, db: Session = Depends(get_db)):
    try:
        return create_and_start_rover(db=db, farmer_id=farmer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start rover: {e}")
    
@router.post("/stop/{session_id}")
def stop (session_id: int, db: Session = Depends(get_db)):
        try:
             return stop_rover(db=db, session_id=session_id)
        except ValueError as e:
             raise HTTPException (status_code= 400, detail = str(e))
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Failed to stop rover: {e}")
    