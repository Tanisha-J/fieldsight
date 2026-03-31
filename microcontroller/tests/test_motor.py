"""
tests/test_motor.py
-------------------
Hardware test script for the FieldSight rover motors.

Run this DIRECTLY on the Raspberry Pi BEFORE writing motor.py.
The goal is to confirm the wiring is correct and the motors behave
as expected. This is NOT the real motor module — it's a one-time
test to verify hardware.

How to run (from the microcontroller/ folder on the Pi):
    python3 tests/test_motor.py

Stages:
    1 — GPIO pin test    : confirms Pi can control GPIO pins (no motors needed)
    2 — Single motor test: tests each motor one at a time (rover on blocks)
    3 — Full rover test  : all 4 motors together (rover on the ground)
"""

import sys
import time

# ─────────────────────────────────────────────
# IMPORT CHECK — CONFIG
# We import config.py first because all our pin numbers live there.
# If this fails it means config.py isn't in the same folder level.
# Fix: make sure you're running from microcontroller/ not from tests/
# ─────────────────────────────────────────────
try:
    import config
except ModuleNotFoundError:
    print("\n[ERROR] Cannot find config.py")
    print("Make sure you run this from the microcontroller/ folder:")
    print("    cd microcontroller")
    print("    python3 tests/test_motor.py\n")
    sys.exit(1)

# ─────────────────────────────────────────────
# IMPORT CHECK — GPIOZERO
# gpiozero is the Python library that lets us control GPIO pins.
# PWMOutputDevice = a pin that can do PWM (variable speed, used for ENA/ENB)
# DigitalOutputDevice = a pin that is just HIGH or LOW (used for IN1-IN4)
# If this fails: pip install gpiozero --break-system-packages
# ─────────────────────────────────────────────
try:
    from gpiozero import PWMOutputDevice, DigitalOutputDevice
except ImportError:
    print("\n[ERROR] gpiozero not installed.")
    print("Run: pip install gpiozero --break-system-packages\n")
    sys.exit(1)


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# Small utilities used throughout the test stages
# ─────────────────────────────────────────────

def prompt(message):
    """
    Pauses the script and waits for the user to press Enter.
    Used before each stage so you have time to get ready.
    """
    input(f"\n  {message}\n  Press Enter when ready...")
    print()

def banner(title):
    """Prints a section header so it's easy to see where you are in the test."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def result(label, passed, detail=""):
    """
    Prints a PASS or FAIL line for a specific check.
    Returns the passed boolean so we can track overall test status.
    """
    icon = "PASS" if passed else "FAIL"
    line = f"  [{icon}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return passed


# ─────────────────────────────────────────────
# MOTOR SETUP HELPER
# This creates a minimal motor object for ONE motor channel.
# It mirrors exactly what motor.py will need to implement later.
# We define it here so the test doesn't depend on motor.py existing yet.
#
# How an L298N motor channel works:
#   IN1=HIGH, IN2=LOW  → motor spins forward
#   IN1=LOW,  IN2=HIGH → motor spins backward
#   IN1=LOW,  IN2=LOW  → motor coasts to stop
#   ENA = PWM value    → controls speed (0.0=off, 1.0=full, 0.45=cruise)
# ─────────────────────────────────────────────

def make_motor(en_pin, in1_pin, in2_pin):
    """
    Creates and returns a minimal motor controller for one channel.

    Parameters:
        en_pin  : GPIO pin number for ENA or ENB (speed control via PWM)
        in1_pin : GPIO pin number for IN1 or IN3 (direction)
        in2_pin : GPIO pin number for IN2 or IN4 (direction)

    Returns a dict with forward, backward, stop, and cleanup functions.
    This is the exact same API that motor.py will expose as a class.
    """
    # Set up the three pins for this motor channel
    en  = PWMOutputDevice(en_pin)       # PWM pin — controls speed
    in1 = DigitalOutputDevice(in1_pin)  # direction pin 1
    in2 = DigitalOutputDevice(in2_pin)  # direction pin 2

    def forward(speed=config.CRUISE_PWM):
        # Clamp speed so it never exceeds MAX_PWM even if called wrong
        speed = min(speed, config.MAX_PWM)
        in1.on()          # IN1 HIGH
        in2.off()         # IN2 LOW  → forward direction
        en.value = speed  # set speed via PWM

    def backward(speed=config.CRUISE_PWM):
        speed = min(speed, config.MAX_PWM)
        in1.off()         # IN1 LOW
        in2.on()          # IN2 HIGH → backward direction
        en.value = speed

    def stop():
        en.value = 0  # cut power first
        in1.off()     # then clear direction pins
        in2.off()

    def cleanup():
        # Release all GPIO pins when done so they don't stay in a bad state
        stop()
        en.close()
        in1.close()
        in2.close()

    return {
        "forward":  forward,
        "backward": backward,
        "stop":     stop,
        "cleanup":  cleanup
    }


# ─────────────────────────────────────────────
# STAGE 1 — GPIO PIN OUTPUT TEST
# Tests that every direction pin and PWM pin can be controlled.
# No motors need to be connected for this.
# Use a multimeter on the GPIO pins to watch them go HIGH/LOW.
# ─────────────────────────────────────────────

def test_pin_outputs():
    banner("STAGE 1 — GPIO pin output test (no motors needed)")

    print("""
  What this does:
    Sets each direction pin HIGH for 1 second then LOW.
    Ramps each PWM pin from 0% to 100% then back to 0%.

  What to look for:
    With a multimeter: direction pins toggle between 0V and 3.3V.
    PWM pins show varying voltage as duty cycle changes.
    Without a multimeter: just confirm no errors are printed.
    """)

    prompt("Ready to start pin test.")

    # All direction pins from config — left driver and right driver
    direction_pins = [
        ("LEFT  IN1", config.MOTOR_LEFT_IN1),
        ("LEFT  IN2", config.MOTOR_LEFT_IN2),
        ("LEFT  IN3", config.MOTOR_LEFT_IN3),
        ("LEFT  IN4", config.MOTOR_LEFT_IN4),
        ("RIGHT IN1", config.MOTOR_RIGHT_IN1),
        ("RIGHT IN2", config.MOTOR_RIGHT_IN2),
        ("RIGHT IN3", config.MOTOR_RIGHT_IN3),
        ("RIGHT IN4", config.MOTOR_RIGHT_IN4),
    ]

    # All PWM speed pins from config
    pwm_pins = [
        ("LEFT  ENA", config.MOTOR_LEFT_ENA),
        ("LEFT  ENB", config.MOTOR_LEFT_ENB),
        ("RIGHT ENA", config.MOTOR_RIGHT_ENA),
        ("RIGHT ENB", config.MOTOR_RIGHT_ENB),
    ]

    passed = True

    # ── Test direction pins ──
    print("  Testing direction pins (HIGH for 1s then LOW)...\n")
    devices = []
    for label, pin in direction_pins:
        try:
            d = DigitalOutputDevice(pin)
            devices.append((label, pin, d))
        except Exception as e:
            # If a pin fails to initialize, note it and keep going
            result(f"Init GPIO{pin} ({label})", False, str(e))
            passed = False

    for label, pin, dev in devices:
        print(f"    GPIO{pin:>2} ({label}) → HIGH", end="", flush=True)
        dev.on()
        time.sleep(0.8)
        dev.off()
        print(" → LOW  ✓")
        time.sleep(0.2)

    # Release all direction pin devices
    for _, _, dev in devices:
        dev.close()

    # ── Test PWM pins ──
    print("\n  Testing PWM pins (ramp 0% → 100% → 0%)...\n")
    pwm_devices = []
    for label, pin in pwm_pins:
        try:
            d = PWMOutputDevice(pin)
            pwm_devices.append((label, pin, d))
        except Exception as e:
            result(f"Init PWM GPIO{pin} ({label})", False, str(e))
            passed = False

    for label, pin, dev in pwm_devices:
        print(f"    GPIO{pin:>2} ({label}) ramping...", end="", flush=True)
        # Step through increasing then decreasing duty cycle values
        for v in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4, 0.2, 0.0]:
            dev.value = v
            time.sleep(0.1)
        print(" done ✓")

    for _, _, dev in pwm_devices:
        dev.close()

    print()
    result("All GPIO pins toggled without errors", passed)
    return passed


# ─────────────────────────────────────────────
# STAGE 2 — SINGLE MOTOR TEST
# Tests each motor channel individually.
# Rover must be elevated so wheels spin freely.
# ─────────────────────────────────────────────

def test_single_motors():
    banner("STAGE 2 — Single motor test (rover on blocks)")

    print("""
  What this does:
    Spins each motor forward for 2 seconds then backward for 2 seconds.
    Tests one motor at a time so you can watch each wheel individually.

  What to look for:
    Each wheel should spin FORWARD then BACKWARD when commanded.
    If a wheel spins the WRONG way on forward:
      → Do NOT rewire. Swap IN1/IN2 for that motor in config.py.

  IMPORTANT: Prop the rover on blocks before continuing.
    The wheels will spin — you don't want it driving off a table.
    """)

    prompt("Rover is propped on blocks, wheels are off the ground.")

    # Define all 4 motors using pin numbers from config
    # Format: (human readable name, ENA/ENB pin, IN1 pin, IN2 pin)
    motors = [
        ("Motor 1 (front-left)",
         config.MOTOR_LEFT_ENA,  config.MOTOR_LEFT_IN1,  config.MOTOR_LEFT_IN2),

        ("Motor 2 (rear-left)",
         config.MOTOR_LEFT_ENB,  config.MOTOR_LEFT_IN3,  config.MOTOR_LEFT_IN4),

        ("Motor 3 (front-right)",
         config.MOTOR_RIGHT_ENA, config.MOTOR_RIGHT_IN1, config.MOTOR_RIGHT_IN2),

        ("Motor 4 (rear-right)",
         config.MOTOR_RIGHT_ENB, config.MOTOR_RIGHT_IN3, config.MOTOR_RIGHT_IN4),
    ]

    all_passed = True

    for name, en, in1, in2 in motors:
        print(f"\n  ── {name} ──")
        print(f"     ENA=GPIO{en}  IN1=GPIO{in1}  IN2=GPIO{in2}")

        # Create a minimal motor object for this channel
        m = make_motor(en, in1, in2)

        try:
            # Test forward
            print("     → FORWARD (2s) — watch this wheel...")
            m["forward"](config.CRUISE_PWM)
            time.sleep(2.0)
            m["stop"]()
            time.sleep(0.5)

            # Test backward
            print("     → BACKWARD (2s) — watch this wheel...")
            m["backward"](config.CRUISE_PWM)
            time.sleep(2.0)
            m["stop"]()
            time.sleep(0.5)

        except Exception as e:
            # Something went wrong at the code level — print the error
            result(name, False, str(e))
            all_passed = False

        finally:
            # Always clean up GPIO even if something crashes
            m["cleanup"]()

        # Ask for manual confirmation — you're watching the wheel
        fwd_ok  = input(f"     Did '{name}' spin FORWARD correctly? [y/n]: ").strip().lower() == "y"
        back_ok = input(f"     Did '{name}' spin BACKWARD correctly? [y/n]: ").strip().lower() == "y"

        result(f"{name} forward",  fwd_ok)
        result(f"{name} backward", back_ok)

        # If direction was wrong, explain exactly how to fix it
        if not fwd_ok:
            print(f"""
     [FIX] {name} spun the wrong direction on FORWARD.
     Open config.py and swap the two IN pin numbers for this motor.
     Example for Motor 1:
         MOTOR_LEFT_IN1 = 27   ← swap these two lines
         MOTOR_LEFT_IN2 = 17
     Save config.py, push to GitHub, git pull on Pi, rerun test.
            """)
            all_passed = False

        if not back_ok:
            all_passed = False

    print()
    result("All 4 motors passed single motor test", all_passed)
    return all_passed


# ─────────────────────────────────────────────
# STAGE 3 — FULL ROVER TEST
# All 4 motors running together on the ground.
# Tests forward, backward, left turn, right turn, emergency stop.
# ─────────────────────────────────────────────

def make_all_motors():
    """Creates all 4 motor objects using pin numbers from config."""
    return {
        # Left side motors — controlled by left L298N driver
        "m1": make_motor(config.MOTOR_LEFT_ENA,  config.MOTOR_LEFT_IN1,  config.MOTOR_LEFT_IN2),
        "m2": make_motor(config.MOTOR_LEFT_ENB,  config.MOTOR_LEFT_IN3,  config.MOTOR_LEFT_IN4),
        # Right side motors — controlled by right L298N driver
        "m3": make_motor(config.MOTOR_RIGHT_ENA, config.MOTOR_RIGHT_IN1, config.MOTOR_RIGHT_IN2),
        "m4": make_motor(config.MOTOR_RIGHT_ENB, config.MOTOR_RIGHT_IN3, config.MOTOR_RIGHT_IN4),
    }

def stop_all(motors):
    """Stops all 4 motors immediately."""
    for m in motors.values():
        m["stop"]()

def cleanup_all(motors):
    """Releases all GPIO pins for all 4 motors."""
    for m in motors.values():
        m["cleanup"]()

def ramp_forward(motors, target=config.CRUISE_PWM):
    """
    Soft-start: gradually increases speed from 0 to target PWM value.
    Prevents large current spikes that can cause the Pi to reboot.
    RAMP_STEP and RAMP_DELAY_SEC come from config.py.
    """
    # First set direction to forward on all motors at 0 speed
    for m in motors.values():
        m["forward"](0.0)

    # Then step up speed gradually until we reach target
    speed = 0.0
    while speed < target:
        speed = min(speed + config.RAMP_STEP, target)
        for m in motors.values():
            m["forward"](speed)
        time.sleep(config.RAMP_DELAY_SEC)


def test_full_rover():
    banner("STAGE 3 — Full rover movement test (on the ground)")

    print("""
  What this does:
    Drives the rover through forward, backward, left turn, right turn.
    Then tests emergency stop with Ctrl+C.

  What to look for:
    FORWARD  — rover drives straight (slight drift is ok for now)
    BACKWARD — rover drives straight in reverse
    LEFT     — rover curves left (left wheels slower than right)
    RIGHT    — rover curves right (right wheels slower than left)

  Clear about 6 feet of space in all directions before starting.
    """)

    prompt("Rover is on the floor. 6ft clear. Standing clear.")

    motors = make_all_motors()
    all_passed = True

    try:
        # ── Forward with soft-start ramp ──
        print("  → FORWARD with soft-start ramp (3s)...")
        ramp_forward(motors, config.CRUISE_PWM)
        time.sleep(3.0)
        stop_all(motors)
        time.sleep(1.0)

        fwd_ok = input("  Did rover drive FORWARD? [y/n]: ").strip().lower() == "y"
        result("Forward drive", fwd_ok)
        if not fwd_ok:
            all_passed = False

        # ── Backward ──
        print("\n  → BACKWARD (3s)...")
        for m in motors.values():
            m["backward"](config.CRUISE_PWM)
        time.sleep(3.0)
        stop_all(motors)
        time.sleep(1.0)

        back_ok = input("  Did rover drive BACKWARD? [y/n]: ").strip().lower() == "y"
        result("Backward drive", back_ok)
        if not back_ok:
            all_passed = False

        # ── Left turn ──
        # Left wheels slower, right wheels faster = curves left
        print("\n  → TURN LEFT (2s)...")
        motors["m1"]["forward"](config.TURN_INNER_PWM)  # front-left  slow
        motors["m2"]["forward"](config.TURN_INNER_PWM)  # rear-left   slow
        motors["m3"]["forward"](config.TURN_OUTER_PWM)  # front-right fast
        motors["m4"]["forward"](config.TURN_OUTER_PWM)  # rear-right  fast
        time.sleep(2.0)
        stop_all(motors)
        time.sleep(1.0)

        left_ok = input("  Did rover curve LEFT? [y/n]: ").strip().lower() == "y"
        result("Left turn", left_ok)
        if not left_ok:
            all_passed = False

        # ── Right turn ──
        # Right wheels slower, left wheels faster = curves right
        print("\n  → TURN RIGHT (2s)...")
        motors["m1"]["forward"](config.TURN_OUTER_PWM)  # front-left  fast
        motors["m2"]["forward"](config.TURN_OUTER_PWM)  # rear-left   fast
        motors["m3"]["forward"](config.TURN_INNER_PWM)  # front-right slow
        motors["m4"]["forward"](config.TURN_INNER_PWM)  # rear-right  slow
        time.sleep(2.0)
        stop_all(motors)
        time.sleep(1.0)

        right_ok = input("  Did rover curve RIGHT? [y/n]: ").strip().lower() == "y"
        result("Right turn", right_ok)
        if not right_ok:
            all_passed = False

        # ── Emergency stop test ──
        # Confirms Ctrl+C stops the rover instantly.
        # Critical — if this fails the rover cannot be stopped during a real scan.
        print("\n  → EMERGENCY STOP TEST")
        print("  Rover will drive forward. Press Ctrl+C to stop it.")
        prompt("Ready for emergency stop test?")

        try:
            ramp_forward(motors, config.CRUISE_PWM)
            time.sleep(10.0)  # user should press Ctrl+C before this finishes
            stop_all(motors)
        except KeyboardInterrupt:
            # This is the expected outcome
            stop_all(motors)
            print("\n  Ctrl+C received — motors stopped.")

        estop_ok = input("  Did rover stop immediately on Ctrl+C? [y/n]: ").strip().lower() == "y"
        result("Emergency stop", estop_ok)
        if not estop_ok:
            all_passed = False

    except Exception as e:
        print(f"\n  [ERROR] Unexpected error: {e}")
        all_passed = False

    finally:
        # Always clean up GPIO even if something crashes mid-test
        cleanup_all(motors)

    print()
    result("Full rover movement test", all_passed)
    return all_passed


# ─────────────────────────────────────────────
# MAIN — Entry point
# Shows a menu and runs whichever stage you choose.
# ─────────────────────────────────────────────

def main():
    banner("FieldSight — Motor Hardware Test")

    print("""
  Run stages in order for a first-time setup:
    Stage 1 first — no motors needed, just confirms GPIO works
    Stage 2 next  — motors connected, rover on blocks
    Stage 3 last  — rover on the floor, full movement test
    """)

    print("  Choose a stage:")
    print("    1 — GPIO pin output test (no motors needed)")
    print("    2 — Single motor test    (rover on blocks)")
    print("    3 — Full rover test      (rover on the ground)")
    print("    a — Run all stages in order")

    choice = input("\n  Enter choice [1/2/3/a]: ").strip().lower()
    print()

    results = {}

    if choice in ("1", "a"):
        results["stage1"] = test_pin_outputs()

    if choice in ("2", "a"):
        results["stage2"] = test_single_motors()

    if choice in ("3", "a"):
        results["stage3"] = test_full_rover()

    # ── Print final summary ──
    banner("TEST SUMMARY")
    labels = {
        "stage1": "Stage 1 — GPIO pin outputs",
        "stage2": "Stage 2 — Single motor test",
        "stage3": "Stage 3 — Full rover movement",
    }
    overall = True
    for key, label in labels.items():
        if key in results:
            passed = results[key]
            overall = overall and passed
            result(label, passed)

    print()
    if overall:
        print("  All stages passed. Ready to write motor.py.")
    else:
        print("  Some stages failed — fix issues above before writing motor.py.")
    print()


# Only runs if you execute this file directly
# Won't run if another file imports it
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Test interrupted. GPIO cleaned up.\n")
        sys.exit(0)