from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import RoverSession
from app.services.mqtt_service import publish_command
#from datetime import date


def stop_rover (db: Session, session_id:int ) -> dict:
    session= db.query (RoverSession).filter(RoverSession.session_id== session_id).first()
    if not session :
        raise ValueError == (f"Session {session_id} not found")
    if session.status == "Stopped":
        raise ValueError ("Rover is already stopped")

    session.status= "Stopped"
    session.started_at= datetime.now(timezone.utc)
    session.active_command= "stop"
    db.commit()

    publish_command(command="stop", rover_id=session_id, session_id=session_id)

    return {"message": f"Rover stopped for session {session_id}", "status": "Stopped"}