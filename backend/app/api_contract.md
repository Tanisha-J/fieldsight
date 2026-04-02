| Action | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Start Rover** | POST | /rover/start/{session_id} | Starts rover and updates session status to Running |
| **Stop Rover** | POST | /rover/stop/{session_id} | Stops rover and updates session status to Stopped |
| **Register** | POST | /auth/register | Creates new farmer account|
| **Login** | POST | /auth/login | Authenticates farmer and returns JWT token |
| **Get Plant Scans** | GET | /scans/{session_id} | Returns all diseased plants scans for a session |
| **Delete Plant Scans** | DELETE | /scans/{session_id} | Deletes all scans for session | 
| **Upload Scan** | POST | /scans/upload | Recieves image from rover, runs Gemini, stores if diseased|
| **Get Latest Telemerty** | GET | /rover/telemerty/latest/{rover_id} | Returns latest GPS, battery, and heading of rover| 
| **Health Check** | GET | /health| Confirms API is running| 

