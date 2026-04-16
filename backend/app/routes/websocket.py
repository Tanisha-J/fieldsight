import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Scan
from app.services.telemetry_service import get_latest_telemetry


router = APIRouter(tags=["websocket"])


def _scan_payload(scan: Scan) -> dict:
    return {
        "scan_id": scan.scan_id,
        "session_id": scan.session_id,
        "farmer_id": scan.farmer_id,
        "disease_status": scan.disease_status,
        "severity": scan.severity,
        "image_url": scan.image_url,
        "gps_lat": scan.gps_lat,
        "gps_lng": scan.gps_lng,
        "short_explanation": scan.short_explanation,
        "confidence_score": scan.confidence_score,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
    }
    
def _telemetry_payload(row: dict) -> dict:
    return {
        "rover_id": row.get("rover_id"),
        "session_id": row.get("session_id"),
        "battery": row.get("battery"),
        "gps_lat": row.get("gps_lat"),
        "gps_lng": row.get("gps_lng"),
        "heading": row.get("heading"),
        "captured_at": row.get("captured_at").isoformat() if row.get("captured_at") else None,
    }


@router.websocket("/websocket/telemetry/{rover_id}")
#fastapi's dependency injection
async def telemetry_endpoint(websocket: WebSocket, rover_id: int, token: str, db: Session = Depends(get_db)):
    await websocket.accept()
    #checking if rover exists
    rover = db.query(Rover).filter(Rover.id == rover_id).first()
    if not rover:
        await websocket.send_json({"error": "Invalid Rover ID"})
        await websocket.close(code=4004)
        return

    # 2. Import and check Auth
    from app.routes.auth import get_current_user_from_token
    user = get_current_user_from_token(token, db)
    
    if not user or rover.farmer_id != user.id:
        await websocket.send_json({"error": "Unauthorized access to this rover"})
        await websocket.close(code=4003)
        return

    

    last_ts = None
    try:
        while True:
            #get latest row from this session
            row = get_latest_telemetry(db=db, rover_id=rover_id)

            if row: 
                #getting datetime object
                ts = row.get("captured_at")

                if ts ! = last_ts:
                    #telemetry_payload handles dates
                    payload = _telemetry_payload(row)
                    #datetime objects to strings
                    if isinstance(payload.get("captured_at"), datetime):
                        payload["captured_at"] = payload["captured_at"].isoformat()
            
                    await websocket.send_json(
                        {
                            "type": "telemetry.latest",
                            "rover_id": rover_id,
                            "telemetry": payload),
                        }
                    )
                    last_ts = ts

                await asyncio.sleep(1)
        except WebSocketDisconnect:
            print(f"Rover {rover_id} disconnected")
        except Exception as e:
            print(f"WebSocket Error: {e}")

@router.websocket("/websocket/scans/{session_id}")
async def scans_ws(websocket: WebSocket, session_id: int):
    await websocket.accept()
    last_scan_id = 0
    try:
        while True:
            db: Session = SessionLocal()
            try:
                scans = (
                    db.query(Scan)
                    .filter(Scan.session_id == session_id, Scan.scan_id > last_scan_id)
                    .order_by(Scan.scan_id.asc())
                    .all()
                )
            finally:
                db.close()

            for scan in scans:
                await websocket.send_json(
                    {
                        "type": "scan.stored",
                        "session_id": session_id,
                        "scan": _scan_payload(scan),
                        "status": "stored",
                    }
                )
                last_scan_id = scan.scan_id

            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        return
