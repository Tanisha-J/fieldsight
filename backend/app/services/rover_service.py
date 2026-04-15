from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import RoverSession
from app.services.mqtt_service import publish_command

def create_and_start_rover(db: Session, farmer_id:int) -> dict:
    session= RoverSession(
        farmer_id=farmer_id,
        rover_id=1,
        session_date= date.today(),
        status="Running",
        active_command= "start",
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    publish_command(
        command= "start",
        rover_id= session.rover_id,
        session_id= session.session_id
    )

    return{
        "session_id": session.session_id,
        "rover_id": session.rover_id,
        "status": session.status,
    }

def stop_rover(db:Session, session_id: int) -> dict:
    session= db.query(RoverSession).filter(RoverSession.session_id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")
    if session.status == "Stopped":
        raise ValueError("Rover is already stopped")
    
    session.status= "Stopped"
    session.stopped_at= datetime.now (timezone.utc)
    session.active_command= "stop"
    db.commit()
    db.refresh(session)

    publish_command(
        command="stop",
        rover_id=session.rover_id,
        session_id=session.session_id
    )

    return{
        "message": f"Rover stopped for session {session_id}",
        "session_id": session.session_id,
        "rover_id": session.rover_id,
        "status": "Stopped"
    }