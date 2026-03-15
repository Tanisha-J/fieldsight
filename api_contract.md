| Action | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Start Rover** | POST | /session/start | Creates a new rover session, sets status to RUNNING |
| **Stop Rover** | POST | /session/stop | Updates session to COMPLETED, sets is_active to false |
| **Register** | POST | /auth/register | Creates a new farmer account |
| **Login** | POST | /auth/login | Authenticates farmer and returns a token |
| **Get Plant Scans** | GET | /scan/{session_id} | Returns all scans with GPS coords and disease status |
| **Delete Plant Scans** | DELETE | /scans/{session_id} | Deletes all scans for a session (Reset Map) |

