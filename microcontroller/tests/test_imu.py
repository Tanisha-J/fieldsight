"""
tests/test_imu.py
-----------------
Hardware test script for the FieldSight IMU (MPU6050).

Run this DIRECTLY on the Raspberry Pi BEFORE writing imu.py.
The goal is to confirm the IMU is wired correctly and returning
real data. This is NOT the real IMU module — it's a one-time
hardware verification test.

How to run (from the microcontroller/ folder on the Pi):
    python3 tests/test_imu.py

Stages:
    1 — I2C bus scan     : confirms Pi can see the IMU at address 0x68
    2 — Wake + raw read  : wakes the chip and reads raw register bytes
    3 — Scaled data      : converts raw values to g and deg/s, checks at rest
    4 — Live stream      : prints live data so you can tilt rover and watch
    5 — Motor noise test : reads IMU while motors run (checks for interference)
"""

import sys
import time
import subprocess

# ─────────────────────────────────────────────
# IMPORT CHECK — CONFIG
# All our IMU settings (I2C address etc) live in config.py
# ─────────────────────────────────────────────
try:
    import config
except ModuleNotFoundError:
    print("\n[ERROR] Cannot find config.py")
    print("Run from the microcontroller/ folder:")
    print("    cd microcontroller")
    print("    python3 tests/test_imu.py\n")
    sys.exit(1)

# ─────────────────────────────────────────────
# IMPORT CHECK — SMBUS2
# smbus2 is the Python library for I2C communication.
# The IMU uses I2C — this is how the Pi talks to it.
# If this fails: pip install smbus2 --break-system-packages
# ─────────────────────────────────────────────
try:
    import smbus2
except ImportError:
    print("\n[ERROR] smbus2 not installed.")
    print("Run: pip install smbus2 --break-system-packages\n")
    sys.exit(1)


# ─────────────────────────────────────────────
# MPU6050 REGISTER ADDRESSES
# The MPU6050 is controlled by reading and writing to specific
# memory addresses (registers) inside the chip over I2C.
# These are the ones we need — documented here so imu.py uses
# the exact same values.
# ─────────────────────────────────────────────

REG_PWR_MGMT_1   = 0x6B  # Power management — write 0x00 here to wake chip from sleep
REG_WHO_AM_I     = 0x75  # Identity check — reading this should return 0x68
REG_ACCEL_XOUT_H = 0x3B  # Start of accel data (6 bytes: X_high, X_low, Y_high, Y_low, Z_high, Z_low)
REG_GYRO_XOUT_H  = 0x43  # Start of gyro data  (6 bytes: same format)
REG_TEMP_OUT_H   = 0x41  # Start of temp data  (2 bytes: high, low)

# How to convert raw numbers to real units
# At default settings the chip uses these scales:
ACCEL_SCALE = 16384.0  # raw units per 1g    (±2g  full scale range)
GYRO_SCALE  = 131.0    # raw units per 1°/s  (±250°/s full scale range)


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def prompt(message):
    """Pauses and waits for Enter before continuing."""
    input(f"\n  {message}\n  Press Enter when ready...")
    print()

def banner(title):
    """Prints a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def result(label, passed, detail=""):
    """Prints a PASS or FAIL line and returns the boolean."""
    icon = "PASS" if passed else "FAIL"
    line = f"  [{icon}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return passed

def raw_to_signed(high_byte, low_byte):
    """
    Combines two bytes into a signed 16-bit integer.
    The MPU6050 stores each reading as two bytes (high and low).
    We need to combine them and handle negative numbers correctly.
    Example: high=0xFF, low=0x38 → raw value → -200 (negative = tilt left)
    """
    value = (high_byte << 8) | low_byte  # combine into one 16-bit number
    if value >= 0x8000:                   # if top bit is set, it's negative
        value -= 0x10000                  # convert to negative
    return value

def read_word(bus, addr, reg):
    """
    Reads two consecutive registers and returns a signed 16-bit int.
    Used for temperature which is stored in just 2 registers.
    """
    high = bus.read_byte_data(addr, reg)      # read high byte
    low  = bus.read_byte_data(addr, reg + 1)  # read low byte
    return raw_to_signed(high, low)

def read_6_bytes(bus, addr, start_reg):
    """
    Reads 6 consecutive registers starting at start_reg.
    Returns three signed 16-bit integers (X, Y, Z).
    Used for both accel and gyro which each have X, Y, Z readings.
    read_i2c_block_data reads multiple bytes in one I2C transaction
    which is faster and more reliable than reading one byte at a time.
    """
    data = bus.read_i2c_block_data(addr, start_reg, 6)  # read all 6 bytes at once
    x = raw_to_signed(data[0], data[1])  # bytes 0-1 = X axis
    y = raw_to_signed(data[2], data[3])  # bytes 2-3 = Y axis
    z = raw_to_signed(data[4], data[5])  # bytes 4-5 = Z axis
    return x, y, z


# ─────────────────────────────────────────────
# STAGE 1 — I2C BUS SCAN
# Runs i2cdetect to confirm the Pi can see the IMU on the I2C bus.
# This is the first thing to check before any Python code touches the chip.
# ─────────────────────────────────────────────

def test_i2c_scan():
    banner("STAGE 1 — I2C bus scan")

    print("""
  What this does:
    Runs the i2cdetect command to scan all I2C addresses.
    We're looking for address 68 (which is 0x68 in hex) to appear.

  What to look for:
    A grid of addresses — 68 should appear somewhere in it.
    If you see all dashes (--) the Pi cannot see the IMU at all.

  If it fails, check:
    SDA wire → GPIO2  (physical pin 3)
    SCL wire → GPIO3  (physical pin 5)
    VCC wire → 3.3V   (physical pin 1) — NOT 5V, that can damage the chip
    GND wire → any GND pin
    I2C enabled: sudo raspi-config → Interface Options → I2C
    """)

    try:
        # Run i2cdetect -y 1  (-y means don't ask for confirmation, 1 = bus 1)
        output = subprocess.check_output(
            ["i2cdetect", "-y", "1"],
            stderr=subprocess.STDOUT
        ).decode()

        print(output)  # print the full grid so you can see it

        # Check if 68 appears anywhere in the output
        detected = "68" in output
        result("MPU6050 detected at address 0x68", detected)

        if not detected:
            print("""
  [FIX] Address 68 not found in the grid.
  Check SDA, SCL, VCC, and GND wiring.
  Also confirm I2C is enabled: sudo raspi-config
            """)

        return detected

    except FileNotFoundError:
        # i2cdetect tool not installed
        print("  [WARN] i2cdetect not found.")
        print("  Install it: sudo apt install i2c-tools")
        print("  Skipping scan — continuing to Stage 2 anyway.")
        return True  # allow test to continue, smbus2 will catch real errors

    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] i2cdetect failed: {e.output.decode()}")
        return False


# ─────────────────────────────────────────────
# STAGE 2 — WAKE CHIP AND READ RAW DATA
# The MPU6050 starts in sleep mode by default.
# We have to write to the power management register to wake it up
# before any sensor data will be valid.
# ─────────────────────────────────────────────

def test_wake_and_raw(bus):
    banner("STAGE 2 — Wake chip and read raw registers")

    addr = config.IMU_I2C_ADDRESS  # 0x68 from config.py
    passed = True

    # ── WHO_AM_I check ──
    # Reading register 0x75 should return 0x68 for a genuine MPU6050.
    # This confirms we're talking to the right chip.
    try:
        who = bus.read_byte_data(addr, REG_WHO_AM_I)
        ok = (who == 0x68)
        result(f"WHO_AM_I register = 0x{who:02X} (expect 0x68)", ok)
        if not ok:
            print("  [WARN] Unexpected WHO_AM_I value.")
            print("  Some clone chips return 0x72 instead. Continuing anyway.")
        passed = passed and ok
    except Exception as e:
        result("WHO_AM_I read", False, str(e))
        print("\n  [ERROR] Cannot communicate with IMU at all.")
        print("  Go back to Stage 1 and fix wiring first.")
        return False

    # ── Wake from sleep ──
    # Writing 0x00 to register PWR_MGMT_1 wakes the chip.
    # Until we do this, all sensor readings will be 0 or garbage.
    try:
        bus.write_byte_data(addr, REG_PWR_MGMT_1, 0x00)
        time.sleep(0.1)  # small delay to let chip finish waking up
        result("Woke chip from sleep (wrote 0x00 to PWR_MGMT_1)", True)
    except Exception as e:
        result("Wake from sleep", False, str(e))
        return False

    # ── Read raw accel ──
    # Just confirms we can read 6 bytes of accelerometer data
    try:
        ax, ay, az = read_6_bytes(bus, addr, REG_ACCEL_XOUT_H)
        result("Raw accel read", True, f"ax={ax:>7d}  ay={ay:>7d}  az={az:>7d}")
    except Exception as e:
        result("Raw accel read", False, str(e))
        passed = False

    # ── Read raw gyro ──
    try:
        gx, gy, gz = read_6_bytes(bus, addr, REG_GYRO_XOUT_H)
        result("Raw gyro  read", True, f"gx={gx:>7d}  gy={gy:>7d}  gz={gz:>7d}")
    except Exception as e:
        result("Raw gyro read", False, str(e))
        passed = False

    # ── Read raw temperature ──
    try:
        temp_raw = read_word(bus, addr, REG_TEMP_OUT_H)
        # Convert raw temp to Celsius using the formula from the MPU6050 datasheet
        temp_c = (temp_raw / 340.0) + 36.53
        result("Raw temp  read", True, f"raw={temp_raw}  →  {temp_c:.1f}°C")
    except Exception as e:
        result("Raw temp read", False, str(e))
        passed = False

    return passed


# ─────────────────────────────────────────────
# STAGE 3 — SCALED DATA SANITY CHECK AT REST
# Converts raw values to real units (g for accel, °/s for gyro)
# and checks they make sense for a rover sitting still on a flat surface.
# ─────────────────────────────────────────────

def test_scaled_at_rest(bus):
    banner("STAGE 3 — Scaled data sanity check at rest")

    print("""
  What this does:
    Takes 20 samples and averages them.
    Converts raw values to g (gravity) and degrees per second.
    Checks the values are physically correct for a still rover.

  Expected values at rest on a flat surface:
    Accel Z ≈ +1.0g   (gravity pulling straight down through the chip)
    Accel X ≈  0.0g   (no tilt forward/back)
    Accel Y ≈  0.0g   (no tilt left/right)
    Gyro X, Y, Z ≈ 0  (not rotating)

  Place rover on a flat surface and keep it completely still.
    """)

    prompt("Rover is flat and completely still.")

    addr = config.IMU_I2C_ADDRESS
    num_samples = 20

    # Accumulate samples then average them to reduce noise
    ax_sum = ay_sum = az_sum = 0.0
    gx_sum = gy_sum = gz_sum = 0.0

    print(f"  Collecting {num_samples} samples...", end="", flush=True)

    for _ in range(num_samples):
        # Read raw values
        ax_r, ay_r, az_r = read_6_bytes(bus, addr, REG_ACCEL_XOUT_H)
        gx_r, gy_r, gz_r = read_6_bytes(bus, addr, REG_GYRO_XOUT_H)

        # Convert to real units by dividing by scale factor
        ax_sum += ax_r / ACCEL_SCALE   # raw → g
        ay_sum += ay_r / ACCEL_SCALE
        az_sum += az_r / ACCEL_SCALE
        gx_sum += gx_r / GYRO_SCALE    # raw → degrees per second
        gy_sum += gy_r / GYRO_SCALE
        gz_sum += gz_r / GYRO_SCALE

        time.sleep(0.05)  # 50ms between samples = ~20 samples per second

    print(" done.\n")

    # Calculate averages
    ax = ax_sum / num_samples
    ay = ay_sum / num_samples
    az = az_sum / num_samples
    gx = gx_sum / num_samples
    gy = gy_sum / num_samples
    gz = gz_sum / num_samples

    # Print the averaged values
    print(f"  Accel X = {ax:+.3f} g    (expect ≈  0.0)")
    print(f"  Accel Y = {ay:+.3f} g    (expect ≈  0.0)")
    print(f"  Accel Z = {az:+.3f} g    (expect ≈ +1.0)")
    print(f"  Gyro  X = {gx:+.2f} °/s  (expect ≈  0.0)")
    print(f"  Gyro  Y = {gy:+.2f} °/s  (expect ≈  0.0)")
    print(f"  Gyro  Z = {gz:+.2f} °/s  (expect ≈  0.0)")
    print()

    passed = True

    # Accel Z should be close to 1.0g — that's gravity pointing down
    az_ok = 0.85 <= az <= 1.15
    result("Accel Z ≈ 1g at rest", az_ok, f"got {az:.3f}g")
    if not az_ok:
        print("  [HINT] If az is close to -1.0, the IMU is mounted upside down.")
        print("  That's fine — just note the sign flip for when you write imu.py.")
    passed = passed and az_ok

    # Accel X and Y should be near zero — rover is flat
    ax_ok = abs(ax) < 0.20
    ay_ok = abs(ay) < 0.20
    result("Accel X ≈ 0 at rest", ax_ok, f"got {ax:.3f}g")
    result("Accel Y ≈ 0 at rest", ay_ok, f"got {ay:.3f}g")
    if not (ax_ok and ay_ok):
        print("  [HINT] Large X or Y means the rover is tilted or the IMU")
        print("  is mounted at an angle. Note the offset for calibration later.")
    passed = passed and ax_ok and ay_ok

    # Gyro should be near zero — rover isn't moving
    gyro_ok = all(abs(v) < 5.0 for v in [gx, gy, gz])
    result("Gyro ≈ 0 at rest", gyro_ok,
           f"gx={gx:.1f}  gy={gy:.1f}  gz={gz:.1f}")
    if not gyro_ok:
        print("  [HINT] Gyro drift > 5°/s at rest is unusual.")
        print("  Wait 30 seconds for the chip to warm up and retry.")
    passed = passed and gyro_ok

    return passed


# ─────────────────────────────────────────────
# STAGE 4 — LIVE DATA STREAM
# Prints a continuous rolling readout of accel and gyro values.
# Pick up and tilt the rover to confirm the axes respond correctly.
# Press Ctrl+C to stop.
# ─────────────────────────────────────────────

def test_live_stream(bus):
    banner("STAGE 4 — Live data stream (Ctrl+C to stop)")

    print("""
  What this does:
    Prints live sensor data 10 times per second.

  What to do:
    Tilt and rotate the rover while watching the numbers.
    Tilting FORWARD  → accel X changes
    Tilting SIDEWAYS → accel Y changes
    SPINNING rover   → gyro Z changes

  This confirms the axes are oriented the way you expect.
  Note down which direction makes which axis go positive —
  you'll need that when writing imu.py.

  Press Ctrl+C when done.
    """)

    prompt("Ready to start live stream.")

    addr   = config.IMU_I2C_ADDRESS
    errors = 0

    # Print header row
    print(f"  {'Ax(g)':>8}  {'Ay(g)':>8}  {'Az(g)':>8}    "
          f"{'Gx(°/s)':>9}  {'Gy(°/s)':>9}  {'Gz(°/s)':>9}")
    print("  " + "-" * 72)

    try:
        while True:
            try:
                # Read accel and gyro
                ax_r, ay_r, az_r = read_6_bytes(bus, addr, REG_ACCEL_XOUT_H)
                gx_r, gy_r, gz_r = read_6_bytes(bus, addr, REG_GYRO_XOUT_H)

                # Convert to real units
                ax = ax_r / ACCEL_SCALE
                ay = ay_r / ACCEL_SCALE
                az = az_r / ACCEL_SCALE
                gx = gx_r / GYRO_SCALE
                gy = gy_r / GYRO_SCALE
                gz = gz_r / GYRO_SCALE

                # Print on same line using \r so it updates in place
                print(
                    f"\r  {ax:>+8.3f}  {ay:>+8.3f}  {az:>+8.3f}    "
                    f"{gx:>+9.2f}  {gy:>+9.2f}  {gz:>+9.2f}",
                    end="",
                    flush=True
                )
                errors = 0  # reset error count on successful read

            except OSError as e:
                # I2C error — count them, fail if too many in a row
                errors += 1
                print(f"\r  [I2C ERROR #{errors}] {e}", end="", flush=True)
                if errors >= 5:
                    print("\n\n  [FAIL] Too many I2C errors. Check wiring.")
                    return False

            time.sleep(0.1)  # 10 readings per second

    except KeyboardInterrupt:
        print("\n\n  Live stream stopped.")

    return True


# ─────────────────────────────────────────────
# STAGE 5 — MOTOR NOISE TEST
# Runs motors at cruise speed while reading the IMU simultaneously.
# Checks that motor electrical noise doesn't corrupt I2C communication.
# This is critical — if motors cause I2C errors during a real scan,
# the rover will lose heading data mid-field.
# ─────────────────────────────────────────────

def test_motor_noise(bus):
    banner("STAGE 5 — IMU reading during motor operation")

    print("""
  What this does:
    Runs all 4 motors at cruise speed for 10 seconds
    while continuously reading the IMU.
    Counts any I2C errors that happen during motor operation.

  Expected result: 0 errors.

  If you get errors:
    Motor switching creates electrical noise that can corrupt I2C signals.
    Fix: add 100nF ceramic capacitors across each motor's + and - terminals.
    Also make sure IMU wires are not running parallel to motor power wires.

  IMPORTANT: Prop rover on blocks first — wheels will spin.
    """)

    # Need gpiozero for motors — fail gracefully if not installed
    try:
        from gpiozero import PWMOutputDevice, DigitalOutputDevice
    except ImportError:
        print("  [SKIP] gpiozero not available. Skipping motor noise test.")
        return True

    prompt("Rover propped on blocks. Wheels off the ground.")

    addr = config.IMU_I2C_ADDRESS

    # Set up all 4 motors using the same make_motor pattern from test_motor.py
    # We inline this here so test_imu.py doesn't depend on test_motor.py
    motor_configs = [
        (config.MOTOR_LEFT_ENA,  config.MOTOR_LEFT_IN1,  config.MOTOR_LEFT_IN2),
        (config.MOTOR_LEFT_ENB,  config.MOTOR_LEFT_IN3,  config.MOTOR_LEFT_IN4),
        (config.MOTOR_RIGHT_ENA, config.MOTOR_RIGHT_IN1, config.MOTOR_RIGHT_IN2),
        (config.MOTOR_RIGHT_ENB, config.MOTOR_RIGHT_IN3, config.MOTOR_RIGHT_IN4),
    ]

    # Create pin objects for all motors
    motors = []
    for en_pin, in1_pin, in2_pin in motor_configs:
        motors.append({
            "en":  PWMOutputDevice(en_pin),
            "in1": DigitalOutputDevice(in1_pin),
            "in2": DigitalOutputDevice(in2_pin),
        })

    def start_all():
        """Sets all motors spinning forward at cruise speed."""
        for m in motors:
            m["in1"].on()
            m["in2"].off()
            m["en"].value = config.CRUISE_PWM

    def stop_all():
        """Stops all motors."""
        for m in motors:
            m["en"].value = 0
            m["in1"].off()
            m["in2"].off()

    def cleanup_all():
        """Releases all GPIO pins."""
        stop_all()
        for m in motors:
            m["en"].close()
            m["in1"].close()
            m["in2"].close()

    # Run the test
    duration   = 10.0  # seconds to run motors
    errors     = 0     # count of I2C errors
    reads      = 0     # count of successful IMU reads
    start_time = time.time()

    print(f"  Running motors for {duration:.0f}s while reading IMU...\n")

    try:
        start_all()

        while time.time() - start_time < duration:
            try:
                # Try to read accel — if this fails during motor operation
                # it means electrical noise is corrupting the I2C bus
                read_6_bytes(bus, addr, REG_ACCEL_XOUT_H)
                reads += 1
            except OSError:
                errors += 1

            elapsed = time.time() - start_time
            print(
                f"\r  t={elapsed:4.1f}s  successful reads={reads:>4}  i2c errors={errors:>3}",
                end="",
                flush=True
            )
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n  Interrupted early.")

    finally:
        stop_all()
        cleanup_all()

    print(f"\n\n  Final: {reads} successful reads, {errors} I2C errors in {duration:.0f}s")

    passed = errors == 0
    result("Zero I2C errors during motor operation", passed)

    if not passed:
        print("""
  [FIX] Add 100nF ceramic capacitors across each motor's terminals.
  Also route IMU wires away from motor power cables.
        """)

    return passed


# ─────────────────────────────────────────────
# MAIN — Entry point
# ─────────────────────────────────────────────

def main():
    banner("FieldSight — IMU Hardware Test")

    print("""
  Run stages in order for first-time setup:
    Stage 1 — confirm I2C scan shows address 68
    Stage 2 — wake chip and confirm raw reads work
    Stage 3 — confirm scaled values are sensible at rest
    Stage 4 — live stream to see axes respond to movement
    Stage 5 — confirm motors don't corrupt IMU reads
    """)

    print("  Choose a stage:")
    print("    1 — I2C bus scan")
    print("    2 — Wake chip + raw register read")
    print("    3 — Scaled sanity check at rest")
    print("    4 — Live data stream")
    print("    5 — Motor noise test")
    print("    a — Run all stages in order")

    choice = input("\n  Enter choice [1/2/3/4/5/a]: ").strip().lower()
    print()

    # Open the I2C bus once and share it across all stages
    # Bus 1 is the standard I2C bus on the Pi's GPIO header
    try:
        bus = smbus2.SMBus(1)
    except Exception as e:
        print(f"\n  [ERROR] Cannot open I2C bus: {e}")
        print("  Make sure I2C is enabled: sudo raspi-config → Interface Options → I2C")
        sys.exit(1)

    results = {}

    try:
        if choice in ("1", "a"):
            results["stage1"] = test_i2c_scan()

        if choice in ("2", "a"):
            results["stage2"] = test_wake_and_raw(bus)

        if choice in ("3", "a"):
            results["stage3"] = test_scaled_at_rest(bus)

        if choice in ("4", "a"):
            results["stage4"] = test_live_stream(bus)

        if choice in ("5", "a"):
            results["stage5"] = test_motor_noise(bus)

    finally:
        # Always close the I2C bus when done
        bus.close()

    # ── Print final summary ──
    banner("TEST SUMMARY")
    labels = {
        "stage1": "Stage 1 — I2C bus scan",
        "stage2": "Stage 2 — Wake + raw read",
        "stage3": "Stage 3 — Scaled sanity check",
        "stage4": "Stage 4 — Live stream",
        "stage5": "Stage 5 — Motor noise test",
    }
    overall = True
    for key, label in labels.items():
        if key in results:
            passed = results[key]
            overall = overall and passed
            result(label, passed)

    print()
    if overall:
        print("  All stages passed. Ready to write imu.py.")
    else:
        print("  Some stages failed — fix issues above before writing imu.py.")
    print()


# Only runs if you execute this file directly
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Test interrupted.\n")
        sys.exit(0)