# FieldSight 🛰️
A minimal viable product autonomous crop disease detection rover.

## Project Structure
- **/frontend**: React + CSS + Mapbox GL JS
- **/backend**: FastAPI + MySQL + Gemini AI + OCI
- **/microcontroller**: Raspberry Pi Hardware Control (motor, GPS, camera)

### Backend Set Up Instructions
- navigate to the backend folder
- run <pip install -r requirements.txt>
- run <schema.sql> in your mysql workbench
- create .env file to add local database credentials

### Frontend Set Up Instructions
- use this link to access the frontend repo connected to Vercel
- https://github.com/tiyaG/FieldSight_frontend

## API Contract
we need to do this contract to define our features and write down the endpoints to keep transparency between the frontend and backend.
i have noted down some key features but it is yall's responsibility to finish it as you work.

## Microcontroller Overview
The microcontroller system uses a Raspberry Pi 4.

### Features
- Controls rover movement (motor module)
- Captures crop images (camera module)
- Retrieves GPS coordinates (gps module)

### Analysis Data Flow
Camera/GPS → Raspberry Pi → Backend → Gemini API → Database → Frontend

