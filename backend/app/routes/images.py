from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Scan, RoverSession, Farmer
from app.services.image_analysis_service import analyze_image
from app.services.image_analysis_service import ImageAnalysisError
from app.services.oci_service import upload_to_oci
from app.services.oci_service import delete_from_oci
from google.genai.errors import ServerError
from app.auth import get_current_user
from app.models import Farmer
import base64
import binascii

router = APIRouter()

@router.get("/scans/{session_id}")
def get_scans(session_id: int, 
              db: Session = Depends(get_db),
              current_user: Farmer = Depends(get_current_user)
              ):
    session= db.query(RoverSession).filter(RoverSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.farmer_id != current_user.farmer_id:
        raise HTTPException(status_code=403, detail="Not authorized to view scans for this session")
    
    scans = db.query(Scan).filter(Scan.session_id == session_id).all()
    return scans

@router.delete("/scans/{session_id}")
def delete_scans(session_id: int, 
                 db: Session = Depends(get_db), 
                 current_user: Farmer = Depends(get_current_user)
                 ):
    
    session = db.query(RoverSession).filter(RoverSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.farmer_id != current_user.farmer_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete scans for this session")

    scans = db.query(Scan).filter(Scan.session_id == session_id).all()
    if not scans:
        raise HTTPException(status_code=404, detail="No scans found for this session")
    
    failed_keys = []
    for scan in scans:
        if scan.image_key:
            try:
                delete_from_oci(scan.image_key)
            except Exception:
                failed_keys.append(scan.image_key)
            
    db.query(Scan).filter(Scan.session_id == session_id).delete()
    db.commit()
    
    return {
        "message": f"All scans deleted for session {session_id}",
        "oci_delete_failed_keys": failed_keys,
    }


@router.post("/scans/upload")
async def upload_scan(
    session_id: int = Form(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user),
):
    image_bytes = await image.read()
    # making sure this is a valid session
    session = db.query(RoverSession).filter(RoverSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.farmer_id != current_user.farmer_id:
        raise HTTPException(status_code=403, detail="Not authorized to upload to this session")
    #1. send to gemini
    try:
        result = await analyze_image(image_bytes)
    except ImageAnalysisError as e:
        raise HTTPException(status_code=502, detail=f"Image analysis failed: {e}")
    except ServerError:
        raise HTTPException(
            status_code=503,
            detail="Image analysis temporarily unavailable (model overloaded). Please retry."
    )


    #2. if healthy
    if result["disease_status"] in ("HEALTHY", "NO PLANT"):
        return {"status": "discarded", "disease_status": result["disease_status"]}
    
    #3. upload to oci
    image_url = None
    image_key = None
    try:
        image_url, image_key = upload_to_oci(image_bytes, image.filename or "scan.jpg")
        #4. save to db
        scan = Scan(
            session_id=session_id,
            farmer_id=current_user.farmer_id,
            disease_status=result["disease_status"],
            severity=result["severity"],
            image_url=image_url,
            image_key=image_key,
            gemini_status="completed",
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            short_explanation=result.get("short_explanation"),
            confidence_score=result.get("confidence_score"),
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
    except Exception as e:
        db.rollback()
        # If DB fails, we MUST delete from OCI or we pay for "ghost" files
        if image_key:
            try:
                delete_from_oci(image_key)
            except Exception:
                pass 
        raise HTTPException(status_code=500, detail=f"database failed: {str(e)}")
    
    return {
        "status": "stored",
        "scan_id": scan.scan_id,
        "image_url": image_url,
        "disease_status": result["disease_status"],
        "severity": result["severity"],
        "short_explanation": result.get("short_explanation"),
        "confidence_score": result.get("confidence_score"),
    }


@router.post("/scans/upload-base64")
async def upload_scan_base64(
    session_id: int = Form(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    image_base64: str = Form(...),
    filename: str = Form("scan.jpg"),
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
        # making sure this is a valid session
        session = db.query(RoverSession).filter(RoverSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.farmer_id != current_user.farmer_id:
            raise HTTPException(status_code=403, detail="Not authorized to upload to this session")
    except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="Invalid base64 image payload")
    
    try:
        result = await analyze_image(image_bytes)
    except ServerError:
        raise HTTPException(
            status_code=503,
            detail="Image analysis temporarily unavailable (model overloaded). Please retry."
    )
    except ImageAnalysisError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Image analysis failed: {e}",
        )

    if result["disease_status"] in ("HEALTHY", "NO PLANT"):
        return {"status": "discarded", "disease_status": result["disease_status"]}

    image_url = None
    image_key = None
    try:
        image_url, image_key = upload_to_oci(image_bytes, filename)

        scan = Scan(
            session_id=session_id,
            farmer_id=current_user.farmer_id,
            disease_status=result["disease_status"],
            severity=result["severity"],
            short_explanation=result.get("short_explanation"),
            confidence_score=result.get("confidence_score"),
            image_url=image_url,
            image_key=image_key,
            gemini_status="completed",
            gps_lat=gps_lat,
            gps_lng=gps_lng,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
    except Exception:
        db.rollback()
        if image_key:
            try:
                delete_from_oci(image_key)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Database/OCI failure: {str(e)}")

    return {
        "status": "stored",
        "scan_id": scan.scan_id,
        "image_url": image_url,
        "disease_status": result["disease_status"],
        "severity": result["severity"],
        "short_explanation": result.get("short_explanation"),
        "confidence_score": result.get("confidence_score"),
    }