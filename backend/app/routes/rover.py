from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
<<<<<<< HEAD
from app.db import get_db
from app.services.rover_service import start_rover, stop_rover
=======
from datetime import date
from app.db import get_db
from app.models import RoverSession
from app.services.rover_service import stop_rover
from app.services.mqtt_service import publish_command
>>>>>>> origin/feature/backend-setup

router = APIRouter(prefix="/rover", tags=["rover"])

<<<<<<< HEAD
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
=======
@router.post("/start")
def start (session_id: int, db: Session= Depends (get_db)):
    try:
        session = RoverSession(
            farmer_id=farmer_id,
            session_date=date.today(),
            status="Running"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        publish_command(command="start", rover_id=session.session_id, session_id=session.session_id)

        return {"session_id": session.session_id, "status": "Running"}
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
    
>>>>>>> origin/feature/backend-setup
