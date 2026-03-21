# FieldSight 🛰️
Autonomous crop disease detection system.

## Project Structure
- **/frontend**: React + Tailwind + Mapbox
- **/backend**: FastAPI + MySQL + Gemini AI
- **/microcontroller**: Raspberry Pi Hardware Control (motor, GPS, camera)

### Backend Set Up Instructions
- navigate to the backend folder
- run <pip install -r requirements.txt>
- run <schema.sql> in your mysql workbench
- create .env file to add local database credentials

### Frontend Set Up Instructions
- navigate to the frontend folder
- run <npm install> to download all the styling and logic tools
- run <npm run dev> to start the local server
- runs on http://localhost:8000 on default and port 5173 can be used from the Vite dev server

## API Contract
we need to do this contract to define our features and write down the endpoints to keep transparency between the frontend and backend.
i have noted down some key features but it is yall's responsibility to finish it as you work.

## Microcontroller Overview
The microcontroller system uses a Raspberry Pi 4.

### Features
- Controls rover movement (motor module)
- Captures crop images (camera module)
- Retrieves GPS coordinates (gps module)

### Data Flow
Camera/GPS → Raspberry Pi → Backend → Database → UI

### Team Update
We are currently creating placeholder functions so backend can begin testing, starting with camera. 