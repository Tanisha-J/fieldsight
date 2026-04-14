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
        session = RoverSession(
            farmer_id=farmer_id,
            rover_id=1,
            session_date=date.today(),
            status="Running",
            active_command="start"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        mqtt_warning = None
        try:
            publish_command(
                command="start",
                rover_id=rover_id,
                session_id=session.session_id
            )
        except Exception as mqtt_err:
            mqtt_warning = str(mqtt_err)

        return {"session_id": session.session_id, 
                "rover_id":1,
                "status": "Running",
                "mqtt_warning": mqtt_warning
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start rover: {e}")
    

@router.post("/stop/{session_id}")
def stop (session_id: int, db: Session= Depends (get_db)):
    try:
        result= stop_rover(db=db, session_id=session_id)
        return result
    except ValueError as e:
        raise HTTPException (status_code= 400, detail = str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop rover: {e}")
    
