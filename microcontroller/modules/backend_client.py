"""
modules/backend_client.py - FieldSight Backend Communication
=============================================================
Handles all communication between the rover and the backend server.

Two communication channels:
    HTTP  — sends captured images to backend via POST /scan/upload
    MQTT  — publishes telemetry, subscribes to start/stop commands

Usage:
    from modules.backend_client import BackendClient

    client = BackendClient(farmer_id=1)
    client.connect()

    # Send an image with GPS coordinates
    client.upload_scan(
        image_path = "captured_images/left_123.jpg",
        session_id = 1,
        gps_lat    = 37.39,
        gps_lng    = -121.85
    )

    # Publish telemetry
    client.publish_telemetry(
        gps_lat  = 37.39,
        gps_lng  = -121.85,
        heading  = 90.0,
        battery  = 85.5
    )

    client.disconnect()
"""

import json
import time
import logging
import threading
import requests
import paho.mqtt.client as mqtt

import config

log = logging.getLogger(__name__)


class BackendClient:
    """
    Handles HTTP image uploads and MQTT telemetry/commands.

    Example:
        client = BackendClient(farmer_id=1)
        client.connect(on_start=handle_start, on_stop=handle_stop)

        client.upload_scan("image.jpg", session_id=1, gps_lat=37.39, gps_lng=-121.85)
        client.publish_telemetry(gps_lat=37.39, gps_lng=-121.85, heading=0.0, battery=100.0)

        client.disconnect()
    """

    def __init__(self, farmer_id, rover_id=1):
        """
        Parameters:
            farmer_id : int — ID of the farmer from the database
                              passed in from main.py when rover starts
            rover_id  : int — ID of this rover (default 1)
        """
        self.farmer_id  = farmer_id
        self.rover_id   = rover_id
        self.session_id = None    # set when start command received via MQTT

        # HTTP base URL
        self.base_url = config.BACKEND_URL

        # MQTT client
        self._mqtt         = mqtt.Client()
        self._connected    = False
        self._on_start_cb  = None   # callback when start command received
        self._on_stop_cb   = None   # callback when stop command received

        # Telemetry thread
        self._telemetry_thread  = None
        self._telemetry_running = False

    # ─────────────────────────────────────────────
    # CONNECTION
    # ─────────────────────────────────────────────

    def connect(self, on_start=None, on_stop=None):
        """
        Connects to MQTT broker and sets up command listener.

        Parameters:
            on_start : callback function called when start command received
                       receives session_id as argument
                       example: def handle_start(session_id): ...
            on_stop  : callback function called when stop command received
        """
        self._on_start_cb = on_start
        self._on_stop_cb  = on_stop

        # Set up MQTT callbacks
        self._mqtt.on_connect    = self._on_connect
        self._mqtt.on_message    = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

        try:
            log.info(f"Connecting to MQTT broker at {config.MQTT_BROKER_URL}:{config.MQTT_PORT}")
            self._mqtt.connect(
                config.MQTT_BROKER_URL,
                config.MQTT_PORT,
                config.MQTT_KEEPALIVE
            )
            # Start MQTT network loop in background thread
            self._mqtt.loop_start()
            log.info("MQTT connected")

        except Exception as e:
            log.error(f"MQTT connection failed: {e}")
            raise

    def disconnect(self):
        """
        Stops telemetry and disconnects from MQTT broker.
        Call this when rover is shutting down.
        """
        self.stop_telemetry()
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        log.info("MQTT disconnected")

    # ─────────────────────────────────────────────
    # MQTT CALLBACKS
    # ─────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        """Called when MQTT connection is established."""
        if rc == 0:
            self._connected = True
            log.info("MQTT broker connected successfully")
            # Subscribe to command topic
            client.subscribe(config.MQTT_CMD_TOPIC)
            log.info(f"Subscribed to {config.MQTT_CMD_TOPIC}")
        else:
            log.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Called when MQTT connection is lost."""
        self._connected = False
        if rc != 0:
            log.warning(f"Unexpected MQTT disconnect (code {rc}) — will auto-reconnect")

    def _on_message(self, client, userdata, msg):
        """
        Called when a message arrives on subscribed topic.
        Handles start and stop commands from the backend.

        Expected message format:
            {"command": "start", "session_id": 123}
            {"command": "stop"}
        """
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")

            log.info(f"MQTT command received: {command}")

            if command == "start":
                session_id = payload.get("session_id")
                if session_id is None:
                    log.error("Start command missing session_id")
                    return
                self.session_id = session_id
                log.info(f"Start command — session_id={session_id}")
                if self._on_start_cb:
                    self._on_start_cb(session_id)

            elif command == "stop":
                log.info("Stop command received")
                if self._on_stop_cb:
                    self._on_stop_cb()

            else:
                log.warning(f"Unknown command: {command}")

        except json.JSONDecodeError:
            log.error(f"Invalid JSON in MQTT message: {msg.payload}")
        except Exception as e:
            log.error(f"Error handling MQTT message: {e}")

    # ─────────────────────────────────────────────
    # IMAGE UPLOAD (HTTP)
    # ─────────────────────────────────────────────
    def upload_scan(self, image_path, session_id, gps_lat, gps_lng):
        url = f"{self.base_url}{config.ENDPOINT_ANALYZE}"
    
        try:
            import base64
            with open(image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        
            payload = {
                "session_id":   session_id,
                "farmer_id":    self.farmer_id,
                "gps_lat":      gps_lat,
                "gps_lng":      gps_lng,
                "image_base64": image_base64,
                "filename":     "scan.jpg"
            }
        
            response = requests.post(url, json=payload, timeout=config.GEMINI_TIMEOUT_SEC)
        
            if response.status_code == 200:
                result = response.json()
                log.info(f"Upload successful: {result}")
                return result
            else:
                log.error(f"Upload failed: {response.status_code} — {response.text}")
                return None
            
        except Exception as e:
            log.error(f"Upload error: {e}")
            return None
   

    # ─────────────────────────────────────────────
    # TELEMETRY (MQTT)
    # ─────────────────────────────────────────────

    def publish_telemetry(self, gps_lat, gps_lng, heading, battery=None):
        """
        Publishes current rover status to MQTT telemetry topic.
        Frontend polls backend which subscribes to this topic.

        Parameters:
            gps_lat : float — current latitude
            gps_lng : float — current longitude
            heading : float — current heading rate in deg/s from IMU
            battery : float — battery percentage (optional)
        """
        if not self._connected:
            log.warning("MQTT not connected — skipping telemetry")
            return

        payload = {
            "rover_id":  self.rover_id,
            "gps_lat":   gps_lat,
            "gps_lng":   gps_lng,
            "heading":   heading,
            "battery":   battery,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        try:
            self._mqtt.publish(
                config.MQTT_TELEMETRY_TOPIC,
                json.dumps(payload)
            )
            log.debug(f"Telemetry published: lat={gps_lat:.4f} lng={gps_lng:.4f}")
        except Exception as e:
            log.error(f"Telemetry publish failed: {e}")

    def start_telemetry_loop(self, state_machine):
        """
        Starts a background thread that publishes telemetry every
        TELEMETRY_INTERVAL_SEC seconds while the rover is running.

        Parameters:
            state_machine : StateMachine object — used to get current status
        """
        self._telemetry_running = True
        self._telemetry_thread  = threading.Thread(
            target  = self._telemetry_loop,
            args    = (state_machine,),
            daemon  = True
        )
        self._telemetry_thread.start()
        log.info("Telemetry loop started")

    def stop_telemetry(self):
        """Stops the background telemetry publishing thread."""
        self._telemetry_running = False
        if self._telemetry_thread:
            self._telemetry_thread.join(timeout=2.0)
        log.info("Telemetry loop stopped")

    def _telemetry_loop(self, state_machine):
        """
        Background thread — publishes telemetry on a fixed interval.
        Reads current status from state_machine.get_status().
        """
        while self._telemetry_running:
            try:
                status = state_machine.get_status()
                loc    = status.get("location", {})

                self.publish_telemetry(
                    gps_lat = loc.get("lat", 0.0),
                    gps_lng = loc.get("lng", 0.0),
                    heading = 0.0   # heading from IMU not tracked at module level
                )
            except Exception as e:
                log.error(f"Telemetry loop error: {e}")

            time.sleep(config.TELEMETRY_INTERVAL_SEC)