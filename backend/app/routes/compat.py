from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.auth import Farmer, RoverSession,Scan
from app.services.mqtt_service import publish_command
from app.service.rover_service import stop_rover, start_rover
from app.services.telemetry_service import get_latest_telemetry

router = APIRouter(prefix="/api", tags=["compat"])

class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    farm_name: str = Field(min_length=1, max_length=100)

class LoginRequest (BaseModel):
    username:str
    password:str

@router.post("/auth/signup", status_code =201)
def compat_signup(payload:SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user=Farmer(
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
        password=hash_password(payload.password),
        farm_name=payload.farm_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return{
        "farmer_id": user.farmer_id,
        "username": user.username,
        "farm_name":user.farm_name,
        "message": "registration successful" ,
          }


@router.post ("/auth/login")
def compat_login(payload: Loginrequest, db: Session = Depends(get_db)):
    user=db.query(Farmer).filter(Farmer.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid username or password",
        )
    user.last_login= datetime.now (timezone.utc)
    db.commit()

    token = create_access_token (subject=user.username)

    return {
        "access_token": token,
        "token_type": "bearer",
        "farmer_id": user.farmer_id,
        "username": user.username,
        "farm_name": user.farm_name,
    }

@router.post ("/auth/logout")
def compat_logout():
    return {"message": "Logout successful"}

@router.get ("/user/profile")
def compact_user_profile(farmer_id: int, db: Session = Depends(get_db)):
    user = db.query(Farmer).filter(Farmer.farmer_id == farmer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "farmer_id": user.farmer_id,
        "username": user.username,
        "farm_name": user.farm_name,
        "created_at": user.created_at,
        "last_login": user.last_login
    }

@router.post ("/rover/start")
def compat_rover_start(farmer_id: int, db: Session =Depends(get_db)):
    try:
        session= RoverSession(
            farmer_id= 1,
            rover_id=1,
            session_date= date.today(),
            status="Running",
            active_command= "start",
            started_at= datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)


        return {
            "session_id": session.session_id,
            "rover_id": session.rover_id,
            "status": session.status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start rover: {e}")


@router.post("/rover/stop/{session_id}")
def compat_rover_stop(session_id: int, db: Session = Depends(get_db)):
    try:
        return stop_rover(db=db, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop rover: {e}")


@router.get("/rover/status")
def compat_rover_status(db: Session = Depends(get_db)):
    row = get_latest_telemetry(db=db, rover_id=1)
    if not row:
        raise HTTPException(status_code=404, detail="No rover status found")

    return {
        "rover_id": row["rover_id"],
        "battery": row["battery"],
        "gps_lat": row["gps_lat"],
        "gps_lng": row["gps_lng"],
        "heading": row["heading"],
        "captured_at": row["captured_at"],
    }


@router.get("/farm/location")
def compat_farm_location(db: Session = Depends(get_db)):
    row = get_latest_telemetry(db=db, rover_id=1)
    if not row:
        raise HTTPException(status_code=404, detail="No location found")

    return {
        "lat": row["gps_lat"],
        "lng": row["gps_lng"],
    }


@router.get("/farm/history")
def compat_farm_history(farmer_id: int, db: Session = Depends(get_db)):
    scans = (
        db.query(Scan)
        .filter(Scan.farmer_id == farmer_id)
        .order_by(Scan.scanned_at.desc())
        .all()
    )

    return [
        {
            "scan_id": scan.scan_id,
            "session_id": scan.session_id,
            "disease_status": scan.disease_status,
            "severity": scan.severity,
            "image_url": scan.image_url,
            "gps_lat": scan.gps_lat,
            "gps_lng": scan.gps_lng,
            "short_explanation": scan.short_explanation,
            "confidence_score": scan.confidence_score,
            "scanned_at": scan.scanned_at,
        }
        for scan in scans
    ]
