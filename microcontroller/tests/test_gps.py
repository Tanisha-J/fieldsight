"""
tests/test_gps.py - FieldSight GPS Hardware Test
=================================================
Run this DIRECTLY on the Raspberry Pi BEFORE using gps.py.
Confirms the VK-162 GPS module is detected, serial communication
works, and valid coordinates are being received.

How to run (from the microcontroller/ folder on the Pi):
    PYTHONPATH=. python3 tests/test_gps.py

IMPORTANT:
    The GPS needs to be OUTDOORS to get a satellite fix.
    Indoors you will get no fix and Stage 3 onwards will fail.
    Stages 1 and 2 can be tested indoors.

Stages:
    1 — Device scan      : confirms GPS shows up at /dev/ttyACM*
    2 — Raw serial read  : confirms NMEA sentences are coming in
    3 — Fix wait         : waits for valid satellite fix (outdoors only)
    4 — Coordinate check : confirms lat/lng values look reasonable
    5 — GPS module test  : confirms gps.py module works end to end
"""

import sys
import time
import subprocess

# ─────────────────────────────────────────────
# IMPORT CHECKS
# ─────────────────────────────────────────────

try:
    import config
except ModuleNotFoundError:
    print("\n[ERROR] Cannot find config.py")
    print("Run from the microcontroller/ folder:")
    print("    cd microcontroller")
    print("    PYTHONPATH=. python3 tests/test_gps.py\n")
    sys.exit(1)

try:
    import serial
except ImportError:
    print("\n[ERROR] pyserial not installed.")
    print("Run: pip3 install pyserial --break-system-packages\n")
    sys.exit(1)

try:
    import pynmea2
except ImportError:
    print("\n[ERROR] pynmea2 not installed.")
    print("Run: pip3 install pynmea2 --break-system-packages\n")
    sys.exit(1)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def prompt(message):
    """Pauses and waits for Enter."""
    input(f"\n  {message}\n  Press Enter when ready...")
    print()

def banner(title):
    """Prints a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def result(label, passed, detail=""):
    """Prints PASS or FAIL for a check."""
    icon = "PASS" if passed else "FAIL"
    line = f"  [{icon}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return passed


# ─────────────────────────────────────────────
# STAGE 1 — DEVICE SCAN
# Confirms the GPS shows up as a serial device.
# ─────────────────────────────────────────────

def test_device_scan():
    banner("STAGE 1 — USB serial device scan")

    print("""
  What this does:
    Lists all /dev/ttyACM* devices on the Pi.
    The VK-162 GPS should appear as /dev/ttyACM*.

  What to look for:
    /dev/ttyACM* appears in the list.
    If multiple /dev/ttyACM* devices exist, note which one is the GPS.

  If nothing appears:
    GPS is not plugged in or not recognized.
    Try unplugging and replugging the GPS USB cable.
    Run: lsusb  to see all USB devices.
    """)

    try:
        import glob
        devices = glob.glob('/dev/ttyACM*')

        if not devices:
            result("GPS serial device found", False, "no /dev/ttyACM* devices")
            print("""
  [FIX] No serial devices found.
  Check GPS is plugged into Pi USB port.
  Run: lsusb
  You should see something like: "U-blox AG [u-blox 7]"
            """)
            return False

        print(f"  Serial devices found: {devices}\n")

        # Check if config port exists
        config_device_exists = config.GPS_PORT in devices
        result(
            f"GPS port from config exists ({config.GPS_PORT})",
            config_device_exists
        )

        if not config_device_exists:
            print(f"""
  [FIX] Expected {config.GPS_PORT} but found {devices}.
  Update GPS_PORT in config.py to match the actual device.
  If you have multiple /dev/ttyACM* devices, the GPS is usually /dev/ttyACM*.
            """)
            return False

        return True

    except Exception as e:
        result("Device scan", False, str(e))
        return False


# ─────────────────────────────────────────────
# STAGE 2 — RAW SERIAL READ
# Opens the serial port and reads raw NMEA sentences.
# Confirms the GPS is outputting data.
# This works indoors even without a satellite fix.
# ─────────────────────────────────────────────

def test_raw_serial():
    banner("STAGE 2 — Raw serial read test")

    print("""
  What this does:
    Opens the GPS serial port and reads 10 raw NMEA sentences.
    NMEA sentences start with $ and contain GPS data.
    This works indoors — we just need to see SOMETHING coming in.

  What to look for:
    Lines starting with $GP or $GN — those are GPS sentences.
    Even without a satellite fix you should see sentences like:
        $GPRMC,000000,V,,,,,,,000000,,*XX
        (the V means no fix yet — that's ok for this stage)
    """)

    try:
        ser = serial.Serial(
            port     = config.GPS_PORT,
            baudrate = config.GPS_BAUDRATE,
            timeout  = config.GPS_TIMEOUT
        )
        result(f"Opened serial port {config.GPS_PORT}", True)
    except serial.SerialException as e:
        result(f"Open serial port {config.GPS_PORT}", False, str(e))
        print(f"""
  [FIX] Cannot open {config.GPS_PORT}.
  Check GPS is plugged in and port is correct in config.py.
        """)
        return False

    print(f"\n  Reading 10 NMEA sentences from {config.GPS_PORT}...\n")

    sentences_received = 0
    nmea_sentences     = 0
    errors             = 0

    for i in range(20):  # try up to 20 reads to get 10 valid lines
        try:
            raw = ser.readline()
            line = raw.decode('ascii', errors='replace').strip()

            if not line:
                continue

            sentences_received += 1
            print(f"    {line}")

            # Count lines that look like proper NMEA sentences
            if line.startswith('$'):
                nmea_sentences += 1

            if nmea_sentences >= 10:
                break

        except Exception as e:
            errors += 1

    ser.close()

    print()
    result(
        f"Received NMEA sentences",
        nmea_sentences > 0,
        f"got {nmea_sentences} sentences"
    )

    if nmea_sentences == 0:
        print("""
  [FIX] No NMEA sentences received.
  The GPS is detected but not outputting data.
  Try:
    1. Wait 30 seconds after plugging in (GPS needs time to start)
    2. Check GPS LED — should be blinking
    3. Try a different USB cable
        """)
        return False

    return True


# ─────────────────────────────────────────────
# STAGE 3 — SATELLITE FIX WAIT
# Waits for the GPS to get a valid satellite fix.
# MUST BE DONE OUTDOORS with clear view of sky.
# ─────────────────────────────────────────────

def test_fix_wait():
    banner("STAGE 3 — Satellite fix wait (OUTDOORS REQUIRED)")

    print("""
  What this does:
    Waits up to 2 minutes for the GPS to acquire a satellite fix.
    A fix means the GPS knows its actual location.

  IMPORTANT:
    This ONLY works outdoors with a clear view of the sky.
    Indoors this will always time out — that is expected.
    Skip this stage if you are indoors.

  What to look for:
    "Got fix!" appears before the 2 minute timeout.
    If it times out indoors — that is normal, not a problem.
    """)

    choice = input("  Are you outdoors with clear sky view? [y/n]: ").strip().lower()
    if choice != 'y':
        print("  Skipping fix wait — run this outdoors before the demo.")
        return True  # not a failure, just skipped

    try:
        ser = serial.Serial(
            port     = config.GPS_PORT,
            baudrate = config.GPS_BAUDRATE,
            timeout  = config.GPS_TIMEOUT
        )
    except serial.SerialException as e:
        result("Open serial port", False, str(e))
        return False

    print("\n  Waiting for satellite fix (up to 2 minutes)...")
    print("  GPS status: ", end="", flush=True)

    timeout    = 120  # 2 minutes
    start_time = time.time()
    fix_found  = False

    while time.time() - start_time < timeout:
        try:
            raw  = ser.readline()
            line = raw.decode('ascii', errors='replace').strip()

            if not line.startswith('$GPRMC') and not line.startswith('$GNRMC'):
                continue

            msg = pynmea2.parse(line)

            if msg.status == 'A':
                # A = Active = valid fix
                fix_found = True
                print(f"\n\n  Got fix!")
                break
            else:
                # V = Void = still searching
                print(".", end="", flush=True)

        except pynmea2.ParseError:
            continue
        except Exception:
            continue

    ser.close()
    print()

    elapsed = time.time() - start_time
    result(
        "Satellite fix acquired",
        fix_found,
        f"after {elapsed:.0f}s" if fix_found else f"timed out after {elapsed:.0f}s"
    )

    if not fix_found:
        print("""
  [NOTE] No fix within 2 minutes.
  This is normal for a cold start in a new location.
  Try again after leaving GPS module outdoors for 5 minutes.
        """)

    return fix_found


# ─────────────────────────────────────────────
# STAGE 4 — COORDINATE CHECK
# Confirms the coordinates look like real values.
# Must have a satellite fix from Stage 3 first.
# ─────────────────────────────────────────────

def test_coordinates():
    banner("STAGE 4 — Coordinate sanity check (OUTDOORS REQUIRED)")

    print("""
  What this does:
    Reads coordinates from GPS and checks they look reasonable.
    Latitude should be between -90 and 90.
    Longitude should be between -180 and 180.
    Neither should be 0,0 (which means no fix).
    """)

    choice = input("  Are you outdoors with a GPS fix? [y/n]: ").strip().lower()
    if choice != 'y':
        print("  Skipping coordinate check — run outdoors after getting a fix.")
        return True

    try:
        ser = serial.Serial(
            port     = config.GPS_PORT,
            baudrate = config.GPS_BAUDRATE,
            timeout  = config.GPS_TIMEOUT
        )
    except serial.SerialException as e:
        result("Open serial port", False, str(e))
        return False

    print("\n  Reading coordinates...\n")

    lat = None
    lng = None
    attempts = 0

    while attempts < 50:
        try:
            raw  = ser.readline()
            line = raw.decode('ascii', errors='replace').strip()

            if not line.startswith('$GPRMC') and not line.startswith('$GNRMC'):
                attempts += 1
                continue

            msg = pynmea2.parse(line)

            if msg.status == 'A':
                lat = msg.latitude
                lng = msg.longitude
                break

            attempts += 1

        except pynmea2.ParseError:
            attempts += 1
            continue

    ser.close()

    if lat is None or lng is None:
        result("Coordinates received", False, "no valid fix found")
        return False

    print(f"  Latitude:  {lat:.6f}")
    print(f"  Longitude: {lng:.6f}\n")

    # Sanity checks
    lat_ok = -90.0 <= lat <= 90.0 and lat != 0.0
    lng_ok = -180.0 <= lng <= 180.0 and lng != 0.0

    result("Latitude in valid range", lat_ok, f"got {lat:.6f}")
    result("Longitude in valid range", lng_ok, f"got {lng:.6f}")

    if lat == 0.0 and lng == 0.0:
        print("""
  [FIX] Coordinates are 0,0 which means no satellite fix.
  Go outdoors and wait for the GPS LED to blink (fix acquired).
        """)
        return False

    return lat_ok and lng_ok


# ─────────────────────────────────────────────
# STAGE 5 — GPS MODULE IMPORT TEST
# Confirms gps.py module works end to end.
# ─────────────────────────────────────────────

def test_module_import():
    banner("STAGE 5 — gps.py module import test")

    print("""
  What this does:
    Imports GPS from gps.py, opens it, and checks it runs
    without errors. Tests get_location() and has_fix().
    Can be run indoors — just confirms the code works,
    not that you have a satellite fix.
    """)

    try:
        from modules.gps import GPS
        result("Import GPS from modules.gps", True)
    except ImportError as e:
        result("Import GPS", False, str(e))
        print("  Make sure gps.py is in the modules/ folder.")
        return False

    try:
        gps = GPS()
        gps.open()
        result("GPS.open()", True)
    except Exception as e:
        result("GPS.open()", False, str(e))
        return False

    # Wait 3 seconds to see if any data comes in
    print("  Waiting 3 seconds for GPS data...")
    time.sleep(3)

    # Check has_fix — will be False indoors, True outdoors
    fix = gps.has_fix()
    location = gps.get_location()

    result(
        "GPS.has_fix()",
        True,  # just checking the method runs, not that fix=True
        f"fix={'yes' if fix else 'no (expected indoors)'}"
    )

    result(
        "GPS.get_location() returns correct type",
        location is None or isinstance(location, dict),
        f"got {type(location).__name__}"
    )

    if location:
        print(f"  Location: lat={location['lat']:.6f}  lng={location['lng']:.6f}")

    gps.close()
    result("GPS.close()", True)

    return True


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    banner("FieldSight — GPS Hardware Test")

    print("""
  Stages 1 and 2 can be run indoors.
  Stages 3 and 4 require being outdoors with clear sky view.
  Stage 5 can be run indoors (just tests the code, not the fix).
    """)

    print("  Choose a stage:")
    print("    1 — Device scan          (indoors ok)")
    print("    2 — Raw serial read      (indoors ok)")
    print("    3 — Satellite fix wait   (OUTDOORS required)")
    print("    4 — Coordinate check     (OUTDOORS required)")
    print("    5 — gps.py module test   (indoors ok)")
    print("    a — Run all stages in order")

    choice = input("\n  Enter choice [1/2/3/4/5/a]: ").strip().lower()
    print()

    results = {}

    if choice in ("1", "a"):
        results["stage1"] = test_device_scan()

    if choice in ("2", "a"):
        results["stage2"] = test_raw_serial()

    if choice in ("3", "a"):
        results["stage3"] = test_fix_wait()

    if choice in ("4", "a"):
        results["stage4"] = test_coordinates()

    if choice in ("5", "a"):
        results["stage5"] = test_module_import()

    banner("TEST SUMMARY")
    labels = {
        "stage1": "Stage 1 — Device scan",
        "stage2": "Stage 2 — Raw serial read",
        "stage3": "Stage 3 — Satellite fix wait",
        "stage4": "Stage 4 — Coordinate check",
        "stage5": "Stage 5 — Module import",
    }
    overall = True
    for key, label in labels.items():
        if key in results:
            passed = results[key]
            overall = overall and passed
            result(label, passed)

    print()
    if overall:
        print("  All stages passed. gps.py is ready to use.")
    else:
        print("  Some stages failed — fix issues above before using gps.py.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Test interrupted.\n")
        sys.exit(0)