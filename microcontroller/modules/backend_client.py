"""
modules/backend_client.py - FieldSight Backend Communication
=============================================================
Handles all communication between the rover and the backend server.

Two communication channels:
    HTTP  — sends captured images to backend via POST /scans/upload-base64
    MQTT  — publishes telemetry, subscribes to start/stop commands

Usage:
    from modules.backend_client import BackendClient

    client = BackendClient(farmer_id=1)
    client.connect()

    client.upload_scan(
        image_path = "captured_images/left_123.jpg",
        session_id = 1,
        gps_lat    = 37.39,
        gps_lng    = -121.85
    )

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
import os
import base64
import logging
import threading
import requests
import paho.mqtt.client as mqtt

import config

log = logging.getLogger(__name__)

API = "https://api.fieldsightproject.com"


class BackendClient:

    def __init__(self, farmer_id, rover_id=1):
        self.farmer_id  = farmer_id
        self.rover_id   = rover_id
        self.session_id = None

        self.base_url = config.BACKEND_URL

        self._mqtt         = mqtt.Client()
        self._connected    = False
        self._on_start_cb  = None
        self._on_stop_cb   = None

        self._telemetry_thread  = None
        self._telemetry_running = False

    # ─────────────────────────────────────────────
    # CONNECTION
    # ─────────────────────────────────────────────

    def connect(self, on_start=None, on_stop=None):
        self._on_start_cb = on_start
        self._on_stop_cb  = on_stop

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
            self._mqtt.loop_start()
            log.info("MQTT connected")

        except Exception as e:
            log.error(f"MQTT connection failed: {e}")
            raise

    def disconnect(self):
        self.stop_telemetry()
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        log.info("MQTT disconnected")

    # ─────────────────────────────────────────────
    # MQTT CALLBACKS
    # ─────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            log.info("MQTT broker connected successfully")
            client.subscribe(config.MQTT_CMD_TOPIC)
            log.info(f"Subscribed to {config.MQTT_CMD_TOPIC}")
        else:
            log.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            log.warning(f"Unexpected MQTT disconnect (code {rc}) — will auto-reconnect")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            target_rover_id = payload.get("rover_id")

            # ignore commands meant for other rovers
            if target_rover_id is not None and int(target_rover_id) != int(self.rover_id):
                return

            log.info(f"MQTT command received: {command}")

            if command == "start":
                session_id = payload.get("session_id")
                farmer_id = payload.get("farmer_id")  # add this
                if farmer_id:
                    self.farmer_id = int(farmer_id)   # add this
                if session_id is None:
                    log.error("Start command missing session_id")
                    return
                self.session_id = int(session_id)
                log.info(f"Start command — session_id={self.session_id}")
                if self._on_start_cb:
                    self._on_start_cb(self.session_id)
            

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

    def _get_token(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"username": "pi_uploader", "password": "pi_password"},
            timeout=15
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def upload_scan(self, image_path, session_id, gps_lat, gps_lng):
        try:
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"}

            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')

            data = {
                "session_id":   str(session_id),
                "farmer_id":    str(self.farmer_id),
                "gps_lat":      str(gps_lat),
                "gps_lng":      str(gps_lng),
                "image_base64": image_base64,
                "filename":     os.path.basename(image_path)
            }

            r = requests.post(
                f"{API}/scans/upload-base64",
                headers=headers,
                data=data,
                timeout=60
            )

            if r.status_code == 401:
                token = self._get_token()
                headers["Authorization"] = f"Bearer {token}"
                r = requests.post(
                    f"{API}/scans/upload-base64",
                    headers=headers,
                    data=data,
                    timeout=60
                )

            log.info(f"Upload: {r.status_code} {r.text}")
            return r
        except Exception as e:
            log.error(f"Upload error: {e}")
            return None
    
    # ─────────────────────────────────────────────
    # TELEMETRY (MQTT)
    # ─────────────────────────────────────────────

    def publish_telemetry(self, gps_lat, gps_lng, heading, battery=None):
        if not self._connected:
            log.warning("MQTT not connected — skipping telemetry")
            return

        if self.session_id is None:
            log.warning("No active session_id — skipping telemetry")
            return

        payload = {
            "session_id": self.session_id,
            "rover_id":   self.rover_id,
            "gps_lat":    gps_lat,
            "gps_lng":    gps_lng,
            "heading":    heading,
            "battery":    battery,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
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
        self._telemetry_running = True
        self._telemetry_thread  = threading.Thread(
            target  = self._telemetry_loop,
            args    = (state_machine,),
            daemon  = True
        )
        self._telemetry_thread.start()
        log.info("Telemetry loop started")

    def stop_telemetry(self):
        self._telemetry_running = False
        if self._telemetry_thread:
            self._telemetry_thread.join(timeout=2.0)
        log.info("Telemetry loop stopped")

    def _telemetry_loop(self, state_machine):
        while self._telemetry_running:
            try:
                status = state_machine.get_status()
                loc    = status.get("location", {})

                self.publish_telemetry(
                    gps_lat = loc.get("lat", 0.0),
                    gps_lng = loc.get("lng", 0.0),
                    heading = 0.0
                )
            except Exception as e:
                log.error(f"Telemetry loop error: {e}")

            time.sleep(config.TELEMETRY_INTERVAL_SEC)