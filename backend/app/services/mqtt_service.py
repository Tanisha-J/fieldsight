import json
import os
from datetime import datetime, timezone 


import paho.mqtt.client as mqtt # lets code connect to broker, and establish subscribers and publishers
from app.db import SessionLocal
from app.services.telemery_service import store_telemetry


from app.db import SessionLocal

from app.services.telemetry_service import store_telemetry

# getting host from environment variables 
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")

# getting port from environment variables
MQTT_PORT = os.getenv("MQTT_PORT", "1883")

# what the rover publishes telemetry to 
MQTT_TELEMETRY_TOPIC = os.getenv("MQTT_TELEMTRY_TOPIC", "rover/telemetry")

# what the backend publishes commands to 
MQTT_CMD_TOPIC = os.getenv("MQTT_CMD_TOPIC", "rover/cmd")

# the actual MQTT client variable, created when start_mqtt_client() is run
_client: mqtt.Client | None = None


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc) 
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] connected to broker at {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(MQTT_TELEMETRY_TOPIC, qos=1)
    else:
        print(f"[MQTT] connection failed with rc={rc}")


def on_message(client, userdata, msg):
    if msg.topic != MQTT_TELEMETRY_TOPIC:
        return

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print(f"[MQTT] invalid telemetry JSON: {e}")
        return

    db = SessionLocal()
    try:
        store_telemetry(
            db=db,
            rover_id=int(payload["rover_id"]),
            battery=float(payload["battery"]),
            gps_lat=float(payload["gps_lat"]),
            gps_lng=float(payload["gps_lng"]),
            heading=float(payload["heading"]) if payload.get("heading") is not None else None,
            captured_at=_parse_timestamp(payload.get("timestamp")),
        )
        print(f"[MQTT] stored telemetry for rover {payload['rover_id']}")
    except Exception as e:
        db.rollback()
        print(f"[MQTT] telemetry ingest error: {e}")
    finally:
        db.close()


def start_mqtt_client() -> mqtt.Client:
    global _client
    if _client is not None:
        return _client

    print(f"[MQTT] starting client for {MQTT_HOST}:{MQTT_PORT}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    _client = client
    return client


def publish_command(command: str, rover_id: int, value: str | None = None) -> dict:
    client = start_mqtt_client()

    payload = {
        "command": command,
        "rover_id": rover_id,
        "value": value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = client.publish(
        topic=MQTT_CMD_TOPIC,
        payload=json.dumps(payload),
        qos=1,
    )

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError(f"MQTT publish failed with rc={result.rc}")

    return {"topic": MQTT_CMD_TOPIC, "payload": payload}
