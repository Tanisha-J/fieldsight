"""
modules/state_machine.py - FieldSight Rover State Machine
==========================================================
The brain of the FieldSight rover. Controls the full autonomous
scan sequence — driving rows, stopping to capture images, uploading
results in the background, and turning between rows.

This module is imported and run by main.py.

Scan pattern:
    1. Drive row forward (100 inches)
       - Stop 4 times evenly spaced to capture images
       - After each capture, start moving immediately
       - Upload images to backend in background while driving
       - At next stop, wait briefly if upload not done
    2. Turn 90 degrees right
    3. Drive row spacing forward (98 inches)
    4. Turn 90 degrees right
    5. Drive row back (scanning second row)
       - Same 4 stop capture pattern
    6. Scan complete — stop and report

Both cameras capture at every stop:
    Left camera  → images of left crop row
    Right camera → images of right crop row

Usage:
    from modules.state_machine import StateMachine

    sm = StateMachine(backend=backend_client, session_id=123)
    sm.run()
"""

import time
import threading
import logging

import config
from modules.motor  import MotorController
from modules.imu    import IMU
from modules.camera import CameraController
from modules.gps    import GPS

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ROVER STATES
# ─────────────────────────────────────────────

class State:
    IDLE      = "idle"
    DRIVING   = "driving"
    STOPPED   = "stopped"
    CAPTURING = "capturing"
    TURNING   = "turning"
    SPACING   = "spacing"
    COMPLETE  = "complete"
    ERROR     = "error"


class StateMachine:
    """
    Controls the full autonomous scan sequence.

    Parameters:
        backend    : BackendClient — handles HTTP uploads and MQTT
                     pass None to run without backend (testing mode)
        session_id : int — scan session ID from MQTT start command
                     pass None to run without uploading (testing mode)
    """

    def __init__(self, backend=None, session_id=None):
        """
        Creates all module objects.
        Does not start any hardware — call run() to begin.

        Parameters:
            backend    : BackendClient object from main.py
                         if None scan runs in testing mode (no uploads)
            session_id : int — current scan session ID
                         if None images are captured but not uploaded
        """
        self.state      = State.IDLE
        self.motors     = MotorController()
        self.imu        = IMU()
        self.camera     = CameraController()
        self.gps        = GPS()
        self.backend    = backend       # None = testing mode
        self.session_id = session_id    # None = no uploads
        self._stop_check = None

        # Track scan progress
        self.current_row      = 0
        self.captures_done    = 0
        self.results          = []

        # Background upload thread
        self._upload_thread = None

    # ─────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────
    def run(self, stop_check=None):
        self._stop_check = stop_check
        try:
            self._startup()
            if self._stop_check and self._stop_check():
                log.info("Stop requested before scan started")
                return
            self._scan_all_rows()
            self._finish()

        except KeyboardInterrupt:
            log.info("Scan interrupted by user")

        except Exception as e:
            log.error(f"Unexpected error during scan: {e}")
            self.state = State.ERROR

        finally:
            self._emergency_stop()
            self._cleanup()


    # ─────────────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────────────

    def _startup(self):
        """Initializes all hardware and waits for GPS fix."""
        log.info("Rover startup...")

        # Wake IMU
        try:
            self.imu.wake()
            log.info("IMU ready")
        except Exception as e:
            log.warning(f"IMU not available: {e} — continuing without IMU")
            self.imu = None

        # Open GPS
        try:
            self.gps.open()
            log.info("GPS open — waiting for fix...")
            got_fix = self.gps.wait_for_fix(timeout=60)
            if got_fix:
                loc = self.gps.get_location()
                log.info(f"GPS fix: {loc['lat']:.6f}, {loc['lng']:.6f}")
            else:
                log.warning("GPS fix timeout — continuing without coordinates")
        except Exception as e:
            log.warning(f"GPS not available: {e} — continuing without GPS")
            self.gps = None

        # Check cameras
        if not self.camera.cameras_available():
            raise RuntimeError("Cameras not available — cannot start scan")
        log.info("Cameras ready")

        if self.backend is None:
            log.info("Running in TESTING MODE — images captured but not uploaded")
        else:
            log.info(f"Backend connected — session_id={self.session_id}")

        log.info("Startup complete — beginning scan")
        self.state = State.DRIVING

    # ─────────────────────────────────────────────
    # MAIN SCAN LOOP
    # ─────────────────────────────────────────────
    def _scan_all_rows(self):
        for row in range(config.NUM_ROWS):
            if self._stop_check and self._stop_check():
                log.info("Stop requested — aborting scan")
                return
            self.current_row = row
            log.info(f"Starting row {row + 1} of {config.NUM_ROWS}")
            self._scan_row()

            if row < config.NUM_ROWS - 1:
                if self._stop_check and self._stop_check():
                    log.info("Stop requested — aborting between rows")
                    return
                self._navigate_to_next_row()

        log.info("All rows complete")


    def _scan_row(self):
        """
        Drives one row making 4 evenly spaced capture stops.

        At each stop:
            1. Stop motors
            2. Wait for previous upload to finish
            3. Capture both cameras
            4. Start upload in background
            5. Start driving again immediately
        """
    
        for stop_num in range(config.CAPTURES_PER_ROW):
            if self._stop_check and self._stop_check():
                log.info("Stop requested — aborting row")
                self.motors.stop()
                return
            log.info(f"  Driving to capture point {stop_num + 1}/{config.CAPTURES_PER_ROW}")

            # Drive to next capture point
            self.state = State.DRIVING
            self.motors.forward(config.CRUISE_PWM)
            time.sleep(config.DRIVE_BETWEEN_CAPTURES_SEC)

            # Stop
            self.motors.ramp_down()
            self.state = State.STOPPED

            # Wait for previous upload if still running
            if self._upload_thread and self._upload_thread.is_alive():
                log.info("  Waiting for previous upload to finish...")
                self._upload_thread.join(timeout=config.GEMINI_TIMEOUT_SEC)

            # Settle before capture
            time.sleep(config.SCAN_SETTLE_TIME_SEC)

            # Get GPS location
            location = self._get_location()
            log.info(f"  Capturing at stop {stop_num + 1} — {location['lat']:.4f}, {location['lng']:.4f}")

            # Capture both cameras
            self.state = State.CAPTURING
            try:
                left_path, right_path = self.camera.capture_both()
                self.captures_done += 1
                log.info(f"  Captured: left={left_path}  right={right_path}")
            except Exception as e:
                log.error(f"  Capture failed: {e}")
                continue

            # Start upload in background — rover moves while this runs
            self._upload_thread = threading.Thread(
                target = self._upload_images,
                args   = (left_path, right_path, location),
                daemon = True
            )
            self._upload_thread.start()

            log.info("  Moving to next point while uploading in background...")

        # Drive to end of row
        log.info("  Driving to end of row...")
        self.state = State.DRIVING
        self.motors.forward(config.CRUISE_PWM)
        time.sleep(config.DRIVE_BETWEEN_CAPTURES_SEC)
        self.motors.ramp_down()

        # Wait for final upload before turning
        if self._upload_thread and self._upload_thread.is_alive():
            log.info("  Waiting for final upload...")
            self._upload_thread.join(timeout=config.GEMINI_TIMEOUT_SEC)

        log.info(f"  Row {self.current_row + 1} complete")

    def _navigate_to_next_row(self):
        """
        Navigates from end of one row to start of next.
        Pattern: pivot right 90° → drive 98 inches → pivot right 90°
        """
        log.info("Navigating to next row...")
        self.state = State.TURNING

        # First 90 degree turn
        log.info("  Pivoting right 90°...")
        self.motors.pivot_left()
        time.sleep(config.PIVOT_90_SEC)
        self.motors.stop()
        time.sleep(0.5)

        # Drive row spacing
        log.info(f"  Driving {config.ROW_SPACING_FT:.1f} ft to next row...")
        self.state = State.SPACING
        self.motors.forward(config.CRUISE_PWM)
        time.sleep(config.DRIVE_ROW_SPACING_SEC)
        self.motors.ramp_down()
        time.sleep(0.5)

        # Second 90 degree turn — now facing down next row
        log.info("  Pivoting right 90°...")
        self.state = State.TURNING
        self.motors.pivot_left()
        time.sleep(config.PIVOT_90_SEC)
        self.motors.stop()
        time.sleep(0.5)

        log.info("  Aligned with next row")

    # ─────────────────────────────────────────────
    # BACKGROUND IMAGE UPLOAD
    # Runs in separate thread while rover drives
    # ─────────────────────────────────────────────

    def _upload_images(self, left_path, right_path, location):
        """
        Uploads both captured images to the backend.
        Runs in a daemon thread — rover keeps driving while this executes.

        Parameters:
            left_path  : file path to left camera image
            right_path : file path to right camera image
            location   : dict with lat, lng from GPS
        """
        # Skip upload if no backend or no session
        if self.backend is None or self.session_id is None:
            log.info("  [BG] Testing mode — skipping upload")
            return

        for image_path, camera_label in [
            (left_path,  "left"),
            (right_path, "right")
        ]:
            try:
                log.info(f"  [BG] Uploading {camera_label} image: {image_path}")
                result = self.backend.upload_scan(
                    image_path = image_path,
                    session_id = self.session_id,
                    gps_lat    = location.get("lat", 0.0),
                    gps_lng    = location.get("lng", 0.0)
                )
                if result:
                    self.results.append(result)
                    log.info(f"  [BG] {camera_label} upload successful: {result}")
                else:
                    log.warning(f"  [BG] {camera_label} upload returned no result")

            except Exception as e:
                log.error(f"  [BG] {camera_label} upload failed: {e}")

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    def _get_location(self):
        """Returns current GPS coordinates or 0,0 if GPS unavailable."""
        if self.gps is None:
            return {'lat': 0.0, 'lng': 0.0, 'timestamp': 'no_gps'}
        return self.gps.get_location_or_default()

    def _emergency_stop(self):
        """Stops all motors immediately. Always runs even on crash."""
        try:
            self.motors.stop()
            log.info("Motors stopped")
        except Exception:
            pass

    def _finish(self):
        """Logs scan summary when complete."""
        self.state = State.COMPLETE
        log.info("=" * 50)
        log.info("SCAN COMPLETE")
        log.info(f"  Total captures : {self.captures_done}")
        log.info(f"  Total results  : {len(self.results)}")
        log.info("=" * 50)

    def _cleanup(self):
        """Releases all hardware. Always runs even on crash."""
        try:
            self.motors.cleanup()
        except Exception:
            pass
        try:
            if self.imu:
                self.imu.close()
        except Exception:
            pass
        try:
            if self.gps:
                self.gps.close()
        except Exception:
            pass
        log.info("Hardware cleanup complete")

    # ─────────────────────────────────────────────
    # STATUS — for telemetry
    # ─────────────────────────────────────────────

    def get_status(self):
        """
        Returns current rover status.
        Called by backend_client.py telemetry loop every 2 seconds.
        """
        return {
            'state':         self.state,
            'current_row':   self.current_row,
            'captures_done': self.captures_done,
            'location':      self._get_location(),
        }