"""
main.py - FieldSight Rover Entry Point
=======================================
This is the file you run on the Pi to start the rover.

It:
    1. Connects to the MQTT broker
    2. Waits for a start command from the backend
    3. Runs the full scan via state_machine.py
    4. Listens for stop command during scan
    5. Cleans up and goes back to waiting

Usage:
    python3 main.py

Or run it automatically on Pi boot by adding to crontab:
    @reboot cd /home/fieldsight/fieldsight/microcontroller && python3 main.py
"""

import sys
import time
import logging

import config
from modules.state_machine  import StateMachine
from modules.backend_client import BackendClient

# ─────────────────────────────────────────────
# LOGGING SETUP
# Prints timestamps and log levels to terminal
# ─────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = '%(asctime)s  %(levelname)s  %(message)s',
    datefmt = '%H:%M:%S'
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ROVER CONFIGURATION
# Change these to match your deployment
# ─────────────────────────────────────────────

# Farmer ID from the database
# Ask your backend team what value to use for testing
FARMER_ID = 1   # ← update this with real farmer_id

# Rover ID — identifies this specific rover
ROVER_ID  = 1


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    log.info("=" * 50)
    log.info("FieldSight Rover starting up")
    log.info(f"Farmer ID: {FARMER_ID}  Rover ID: {ROVER_ID}")
    log.info("=" * 50)

    # Create backend client
    backend = BackendClient(farmer_id=FARMER_ID, rover_id=ROVER_ID)

    # Track whether a stop was requested mid-scan
    stop_requested = False
    current_session_id = None

    # ── Callbacks for MQTT commands ──────────────────

    def on_start(session_id):
        """Called when backend sends start command via MQTT."""
        nonlocal current_session_id
        current_session_id = session_id
        log.info(f"Start command received — session_id={session_id}")

    def on_stop():
        """Called when backend sends stop command via MQTT."""
        nonlocal stop_requested
        stop_requested = True
        log.info("Stop command received")

    # ── Connect to MQTT ──────────────────────────────

    try:
        backend.connect(on_start=on_start, on_stop=on_stop)
    except Exception as e:
        log.error(f"Cannot connect to MQTT broker: {e}")
        log.error("Check that backend is running and MQTT_BROKER_URL is correct in config.py")
        sys.exit(1)

    # ── Wait for start command ───────────────────────

    log.info("Waiting for start command from backend...")
    log.info(f"Listening on MQTT topic: {config.MQTT_CMD_TOPIC}")

    try:
        while current_session_id is None:
            time.sleep(0.5)

    except KeyboardInterrupt:
        log.info("Interrupted while waiting — shutting down")
        backend.disconnect()
        sys.exit(0)

    # ── Run scan ─────────────────────────────────────

    log.info(f"Starting scan — session_id={current_session_id}")

    # Create state machine with backend client and session info
    sm = StateMachine(
        backend    = backend,
        session_id = current_session_id
    )

    # Start telemetry loop — publishes rover status every 2 seconds
    backend.start_telemetry_loop(sm)

    try:
        sm.run()

    except KeyboardInterrupt:
        log.info("Scan interrupted by user")

    finally:
        backend.stop_telemetry()
        backend.disconnect()
        log.info("Rover shutdown complete")


if __name__ == "__main__":
    main()