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
async def telemetry_endpoint(websocket: WebSocket, rover_id: int):
    await websocket.accept()
    last_ts = None
    try:
        while True:
            db: Session = SessionLocal()
            try:
                row = get_latest_telemetry(db=db, rover_id=rover_id)
            finally:
                db.close()

            ts = row.get("captured_at") if row else None
            if ts != last_ts and row is not None:
                await websocket.send_json(
                    {
                        "type": "telemetry.latest",
                        "rover_id": rover_id,
                        "telemetry": _telemetry_payload(row),
                    }
                )
                last_ts = ts

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print(f"Rover {rover_id} disconnected")


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
