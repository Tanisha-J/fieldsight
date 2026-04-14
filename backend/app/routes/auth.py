from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password, create_access_token
from app.db import get_db
from app.models import Farmer

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=72)
    farm_name: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    try:
        pw_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    
    user = Farmer(
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
        password_hash=pw_hash,
        farm_name=payload.farm_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "farmer_id": user.farmer_id,
        "username": user.username,
        "farm_name": user.farm_name,
        "message": "Registration successful",
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Farmer).filter(Farmer.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token)
