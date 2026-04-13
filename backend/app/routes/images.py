from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Scan
from app.services.oci_service import upload_to_oci
from app.services.oci_service import delete_from_oci
from app.services.image_analysis_service import analyze_image
import base64

router = APIRouter()

@router.get ("/scans/{session_id}")
def get_scans (session_id: int ,db: Session = Depends (get_db)):
    scans=db.query(Scan).filter(Scan.session_id== session_id).all()
    if not scans:
        raise HTTPException(status_code=404, detail="No scans found for this session")
    return scans

@router.delete("/scans/{session_id}")
def delete_scans(session_id: int, db: Session = Depends(get_db)):
    scans = db.query(Scan).filter(Scan.session_id == session_id).all()
    if not scans:
        raise HTTPException(status_code=404, detail="No scans found for this session")
    
    for scan in scans:
        if scan.image_key:
            delete_from_oci(scan.image_key)
            
    db.query(Scan).filter(Scan.session_id == session_id).delete()
    db.commit()
    return {"message": f"All scans deleted for session {session_id}"}

@router.post("/scans/upload")
async def upload_scan(
    session_id: int = Form(...),
    farmer_id: int = Form(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    image_bytes = await image.read()
    #1. send to gemini
    result = await analyze_image(image_bytes)
    #2. if healthy
    if result["disease_status"] in ("HEALTHY"):
        return {"status": "discarded", "disease_status": result["disease_status"]}
    #3. upload to oci
    image_key = upload_to_oci(image_bytes, image.filename)
    #4. save to db
    scan = Scan(
        session_id=session_id,
        farmer_id=farmer_id,
        disease_status=result["disease_status"],
        severity=result["severity"],
        image_key=image_key,
        gemini_status="completed",
        gps_lat=gps_lat,
        gps_lng=gps_lng,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    return {"status": "stored", "scan_id": scan.scan_id}

@router.post("/scan/upload")
async def upload_scan(
    session_id: int = Form(...),
    farmer_id: int = Form(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    image_base64: str = Form(...),
    db: Session = Depends(get_db)
):
    image_bytes = base64.b64decode(image_base64)
    result = await analyze_image(image_bytes)

    if result["disease_status"] == "HEALTHY":
        return {"status": "discarded", "disease_status": result["disease_status"]}

    image_url, image_key = upload_to_oci(image_bytes, "scan.jpg")

    scan = Scan(
        session_id=session_id,
        farmer_id=farmer_id,
        disease_status=result["disease_status"],
        severity=result["severity"],
        symptoms_observed=result["symptoms_observed"],
        image_url=image_url,
        image_key=image_key,
        gemini_status="completed",
        gps_lat=gps_lat,
        gps_lng=gps_lng,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return {"status": "stored", 
            "scan_id": scan.scan_id,
            "image_url": image_url,
            "disease_status":result ["disease_status"],
            "severity": result["severity"],
            "short_explanation": result.get("short_explanation")
            }