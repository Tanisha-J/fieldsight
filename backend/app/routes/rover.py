from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db import get_db
from app.models import RoverSession
from app.services.rover_service import stop_rover
from app.services.mqtt_service import publish_command
from app.auth import get_current_user
from app.models import Farmer

router = APIRouter(prefix="/rover", tags=["rover"])

@router.post("/start")
def start(
     db: Session= Depends(get_db),
     current_user: Famer = Depends(get_current_user),
):
    try:
         session=RoverSession(
              farmer_id=current_user.farmer_id,
              rover_id=1,
              session_date= date.today(),
              status= "Running",
              active_command= "start"
         )
         db.add(session)
         db.commit()
         db.refresh(session)

         mqtt_warning= None
         try:
              publish_command(
                   command= "start",
                   rover_id= session.rover_id,
                   session_id= session.session_id
              )
         except Exception as mqtt_err:
              mqtt_warning= str(mqtt_err)

         return{
             "session_id": session.session_id,
             "rover_id": session.rover_id,
             "status": "Running",
             "mqtt_warning": mqtt_warning
         }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start rover: {e}")
    
@router.post("/stop/{session_id}")
def stop(
     session_id:int,
     db: Session = Depends(get_db),
     current_user: Farmer = Depends(get_current_user),
):
     session= db.query(RoverSession).filter(RoverSession.session_id == session_id).first()
     if not session:
          raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
     if session.farmer_id != current_user.farmer_id:
          raise HTTPException(status_code=403, detail="Not authorized to stop this rover session")
     try:
          return stop_rover(db=db, session_id=session_id)
     except ValueError as e:
          raise HTTPException(status_code=400, detail=str(e))
     except Exception as e:
          raise HTTPException(status_code=500, detail=f"Failed to stop rover: {e}")

    