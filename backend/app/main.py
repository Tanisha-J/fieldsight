from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import rover, images, health, telemetry, auth

app= FastAPI( title= "FieldSight API")


#frontend (react) to talk to backend

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React runs on this port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#register all routes

app.include_router(health.router)
app.include_router(rover.router)
app.include_router(images.router)
app.include_router(telemetry.router)

@app.get("/")
def root():
    return {"message": "FieldSight API is running"}

