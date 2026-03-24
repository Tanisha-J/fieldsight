"""
motor_controller.py
FieldSight Rover - Motor Controller Module
==========================================
Hardware:
  - Raspberry Pi 4 (GPIO + PWM)
  - L298N Dual H-Bridge Motor Driver (x2, one per side)
  - Cytron 12V 37mm DC Motors (x4, tank drive)
  - 10Ah LiFePO4 12V Battery

Tank Drive Layout:
  LEFT SIDE  : Motors A & B  → L298N Driver #1
  RIGHT SIDE : Motors C & D  → L298N Driver #2

L298N Pin Mapping (per driver):
  IN1, IN2  → GPIO direction pins  (HIGH/LOW sets forward or reverse)
  ENA       → PWM pin             (duty cycle 0–100 controls speed)
"""

import RPi.GPIO as GPIO
import time

# ── GPIO Pin Definitions ──────────────────────────────────────────────────────

# Left side (Driver #1)
LEFT_IN1  = 17   # Direction pin A
LEFT_IN2  = 27   # Direction pin B
LEFT_ENA  = 18   # PWM speed pin (must be a hardware PWM-capable pin)

# Right side (Driver #2)
RIGHT_IN1 = 23   # Direction pin A
RIGHT_IN2 = 24   # Direction pin B
RIGHT_ENA = 25   # PWM speed pin (must be a hardware PWM-capable pin)

# ── Constants ─────────────────────────────────────────────────────────────────

PWM_FREQ      = 1000   # Hz  — well within L298N's 25–40 kHz commutation range
DEFAULT_SPEED = 60     # %   — duty cycle (0–100); tuned for ~1 mph target speed
TURN_SPEED    = 50     # %   — slightly slower for controlled 90° turns
TURN_90_TIME  = 0.85   # sec — empirically tuned; adjust after hardware testing


# ── Setup & Teardown ──────────────────────────────────────────────────────────

def setup():
    """Initialize GPIO and PWM. Call once at program start."""
    GPIO.setmode(GPIO.BCM)          # Use Broadcom pin numbering
    GPIO.setwarnings(False)

    # Set all motor pins as outputs
    for pin in [LEFT_IN1, LEFT_IN2, LEFT_ENA,
                RIGHT_IN1, RIGHT_IN2, RIGHT_ENA]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)  # Safe default: motors off

    # Create PWM objects on the Enable pins
    global left_pwm, right_pwm
    left_pwm  = GPIO.PWM(LEFT_ENA,  PWM_FREQ)
    right_pwm = GPIO.PWM(RIGHT_ENA, PWM_FREQ)

    # Start PWM at 0% (stopped)
    left_pwm.start(0)
    right_pwm.start(0)

    print("[MotorController] Setup complete.")


def cleanup():
    """Stop motors and release GPIO. Call on program exit."""
    stop()
    left_pwm.stop()
    right_pwm.stop()
    GPIO.cleanup()
    print("[MotorController] Cleanup complete.")


# ── Low-Level Helpers ─────────────────────────────────────────────────────────

def _set_left(forward: bool, speed: int):
    """
    Drive the left side motors.
    forward=True  → IN1=HIGH, IN2=LOW
    forward=False → IN1=LOW,  IN2=HIGH
    speed: 0–100 (PWM duty cycle)
    """
    GPIO.output(LEFT_IN1, GPIO.HIGH if forward else GPIO.LOW)
    GPIO.output(LEFT_IN2, GPIO.LOW  if forward else GPIO.HIGH)
    left_pwm.ChangeDutyCycle(speed)


def _set_right(forward: bool, speed: int):
    """Drive the right side motors. Same logic as _set_left."""
    GPIO.output(RIGHT_IN1, GPIO.HIGH if forward else GPIO.LOW)
    GPIO.output(RIGHT_IN2, GPIO.LOW  if forward else GPIO.HIGH)
    right_pwm.ChangeDutyCycle(speed)


# ── Public Movement API ───────────────────────────────────────────────────────

def move_forward(speed: int = DEFAULT_SPEED):
    """
    Drive both sides forward at the given speed (0–100%).
    Used for straight-line row traversal.
    """
    _set_left(forward=True,  speed=speed)
    _set_right(forward=True, speed=speed)


def move_backward(speed: int = DEFAULT_SPEED):
    """Reverse both sides. Useful for repositioning."""
    _set_left(forward=False,  speed=speed)
    _set_right(forward=False, speed=speed)


def stop():
    """
    Immediately stop all motors by setting duty cycle to 0.
    Direction pins are left as-is (safe — no current flows at 0%).
    """
    left_pwm.ChangeDutyCycle(0)
    right_pwm.ChangeDutyCycle(0)


def turn_left(duration: float = TURN_90_TIME, speed: int = TURN_SPEED):
    """
    Tank turn left ≈ 90°.
    Left side reverses, right side drives forward → spins in place.
    duration: seconds to run the turn (tune TURN_90_TIME for your surface).
    """
    _set_left(forward=False, speed=speed)
    _set_right(forward=True, speed=speed)
    time.sleep(duration)
    stop()


def turn_right(duration: float = TURN_90_TIME, speed: int = TURN_SPEED):
    """
    Tank turn right ≈ 90°.
    Left side drives forward, right side reverses.
    """
    _set_left(forward=True,  speed=speed)
    _set_right(forward=False, speed=speed)
    time.sleep(duration)
    stop()


def set_speed(speed: int):
    """
    Change speed of both sides while keeping current direction.
    Useful for IMU-based speed corrections mid-row.
    speed: 0–100
    """
    speed = max(0, min(100, speed))   # Clamp to valid range
    left_pwm.ChangeDutyCycle(speed)
    right_pwm.ChangeDutyCycle(speed)


def steer(left_speed: int, right_speed: int):
    """
    Independent speed control for each side.
    Used by the IMU correction loop to fix drift:
      - If rover drifts right → reduce right_speed
      - If rover drifts left  → reduce left_speed
    Both sides assumed to be moving forward.
    """
    left_speed  = max(0, min(100, left_speed))
    right_speed = max(0, min(100, right_speed))
    _set_left(forward=True,  speed=left_speed)
    _set_right(forward=True, speed=right_speed)


# ── Row Navigation Routine ────────────────────────────────────────────────────

def survey_row(row_duration: float, capture_callback=None, capture_interval: float = 2.0):
    """
    Drive forward for `row_duration` seconds, triggering `capture_callback`
    every `capture_interval` seconds (to take a picture every ~2 feet at 1 mph).

    Args:
        row_duration     : Total seconds to traverse one row (~52.5s for 75 ft at 1 mph)
        capture_callback : Function to call for image capture (e.g., camera.capture())
        capture_interval : Seconds between captures (default 2s → ~2 ft at 1 mph)
    """
    move_forward()
    elapsed      = 0.0
    last_capture = 0.0

    while elapsed < row_duration:
        time.sleep(0.1)
        elapsed      += 0.1
        last_capture += 0.1

        if capture_callback and last_capture >= capture_interval:
            capture_callback()
            last_capture = 0.0

    stop()


# ── Quick Smoke Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Run this directly on the Pi to verify wiring before integration:
      python3 motor_controller.py
    """
    setup()
    try:
        print("Forward 2s...")
        move_forward()
        time.sleep(2)
        stop()
        time.sleep(0.5)

        print("Turn left 90°...")
        turn_left()
        time.sleep(0.5)

        print("Forward 2s...")
        move_forward()
        time.sleep(2)
        stop()
        time.sleep(0.5)

        print("Turn right 90°...")
        turn_right()
        time.sleep(0.5)

        print("Backward 1s...")
        move_backward()
        time.sleep(1)
        stop()

        print("Smoke test complete.")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        cleanup()