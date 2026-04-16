| Action | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Health Check** | GET | /health | Verifies the backend server is online and reachable |
| **Get Plant Scans** | GET | /scans/{session_id} | Returns all scans with GPS coords and disease status |
| **Delete Plant Scans** | DELETE | /scans/{session_id} | Deletes all scans for a session (Reset Map) |
| **Upload Scan** | POST | /scans/upload | Uploads a new plant scan image and data |
| **Upload Scan Base64**| POST | /scans/upload-base64 | Uploads a scan using Base64 encoded image data |
| **Root** | GET | / | Base endpoint, usually returns API version or welcome message |
| **Start Rover** | POST | /rover/start | Creates a new rover session and sets status to RUNNING |
| **Stop Rover** | POST | /rover/stop/{session_id} | Updates session to COMPLETED and sets is_active to false |
| **Latest Telemetry** | GET | /rover/telemetry/latest/{rover_id} | Fetches the most recent GPS and sensor data for a rover |
| **Register** | POST | /auth/register | Creates a new farmer account |
| **Login** | POST | /auth/login | Authenticates farmer and returns a JWT/session token |
| **Compat Signup** | POST | /api/auth/signup | Legacy compatible endpoint for user registration |
| **Compat Login** | POST | /api/auth/login | Legacy compatible endpoint for user authentication |
| **Compat Logout** | POST | /api/auth/logout | Legacy compatible endpoint to invalidate a session |
| **Compat User Profile**| GET | /api/user/profile | Fetches profile details for the authenticated user |
| **Compat Rover Start** | POST | /api/rover/start | Legacy compatible endpoint to start a rover session |
| **Compat Rover Stop** | POST | /api/rover/stop/{session_id} | Legacy compatible endpoint to stop a rover session |
| **Compat Rover Status**| GET | /api/rover/status | Fetches current status/availability of the rover |
| **Compat Farm Location**| GET | /api/farm/location | Returns the boundary/GPS coordinates of the farm |
| **Compat Farm History**| GET | /api/farm/history | Fetches historical data for past rover runs and scans |