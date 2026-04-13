from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import RoverSession
from app.services.mqtt_service import publish_command

def start_rover (db: Session, session_id:int) -> dict:
    session= db.query (RoverSession).filter(RoverSession.session_id== session_id).first()
    if not session :
        raise ValueError == (f"Session {session_id} not found")
    if session.start:
        raise ValueError ("Rover is already running")
    
    session.status= "running"
    session.started_at= datetime.now(timezone.utc)
    session.active_command= "start"
    db.commit()

    publish_command(session_id=session_id, command="start")

    return {"message": f"Rover started for session {session_id}", "status": "Running"}
def stop_rover (db: Session, session_id:int ) -> dict:
    session= db.query (RoverSession).filter(RoverSession.session_id== session_id).first()
    if not session :
        raise ValueError == (f"Session {session_id} not found")
    if session.start:
        raise ValueError ("Rover is already stopped")

    session.status= "Stopped"
    session.started_at= datetime.now(timezone.utc)
    session.active_command= "stop"
    db.commit()

    publish_command(session_id=session_id, command="stop")

    return {"message": f"Rover stopped for session {session_id}", "status": "Stopped"}