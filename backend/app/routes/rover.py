from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.rover_service import start_rover, stop_rover

router = APIRouter(prefix="/rover", tags=["rover"])

@router.post("/start/{session_id}")
def start(session_id: int, db: Session = Depends(get_db)):
    try:
        result = start_rover(db=db, session_id=session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start rover: {e}")

@router.post("/stop/{session_id}")
def stop(session_id: int, db: Session = Depends(get_db)):
    try:
        result = stop_rover(db=db, session_id=session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop rover: {e}")