"""
tests/test_camera.py - FieldSight Camera Hardware Test
=======================================================
Run this DIRECTLY on the Raspberry Pi BEFORE using camera.py.
Confirms both USB cameras are detected, OpenCV can open them,
and images are being captured and saved correctly.

How to run (from the microcontroller/ folder on the Pi):
    PYTHONPATH=. python3 tests/test_camera.py

Stages:
    1 — Device scan      : confirms Pi can see cameras at /dev/video*
    2 — OpenCV open      : confirms OpenCV can open both cameras
    3 — Single capture   : captures one frame from each camera
    4 — Both capture     : captures from both cameras at same time
    5 — Save test        : confirms images are saved to disk correctly
"""

import sys
import os
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
    print("    PYTHONPATH=. python3 tests/test_camera.py\n")
    sys.exit(1)

try:
    import cv2
except ImportError:
    print("\n[ERROR] OpenCV not installed.")
    print("Run: sudo apt install python3-opencv -y\n")
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
# Checks what video devices the Pi can see.
# Both cameras should show up as /dev/video0, /dev/video1, etc.
# ─────────────────────────────────────────────

def test_device_scan():
    banner("STAGE 1 — USB video device scan")

    print("""
  What this does:
    Lists all video devices the Pi can see.
    Each USB camera shows up as /dev/videoN where N is the index.

  What to look for:
    At least two devices listed (one per camera).
    Note which indexes appear — you need them for config.py.

  If you see fewer devices than expected:
    One camera may not be plugged in or recognized.
    Try unplugging and replugging each camera.
    """)

    try:
        # List all /dev/video* devices
        output = subprocess.check_output(
            ["ls", "/dev/video*"],
            stderr=subprocess.STDOUT,
            shell=False
        ).decode().strip()
        print(f"\n  Devices found:\n    {output}\n")
    except subprocess.CalledProcessError:
        # ls returns error if no files match
        try:
            # Try alternate approach
            import glob
            devices = glob.glob('/dev/video*')
            if devices:
                print(f"\n  Devices found: {devices}\n")
            else:
                result("Video devices found", False, "no /dev/video* devices found")
                print("""
  [FIX] No cameras detected.
  Check that both USB cameras are plugged in.
  Try: lsusb  to see all USB devices connected to the Pi.
                """)
                return False
        except Exception as e:
            result("Device scan", False, str(e))
            return False

    # Try listing with v4l2-ctl for more detail
    try:
        detail = subprocess.check_output(
            ["v4l2-ctl", "--list-devices"],
            stderr=subprocess.STDOUT
        ).decode()
        print("  Detailed device list:")
        for line in detail.strip().split('\n'):
            print(f"    {line}")
        print()
    except FileNotFoundError:
        print("  [INFO] v4l2-ctl not installed — skipping detailed scan.")
        print("  Install for more detail: sudo apt install v4l-utils -y\n")
    except subprocess.CalledProcessError:
        pass

    # Check config indexes exist as devices
    front_device = f"/dev/video{config.CAMERA_FRONT_INDEX}"
    side_device  = f"/dev/video{config.CAMERA_SIDE_INDEX}"

    front_exists = os.path.exists(front_device)
    side_exists  = os.path.exists(side_device)

    result(
        f"Front camera device exists ({front_device})",
        front_exists
    )
    result(
        f"Side camera device exists ({side_device})",
        side_exists
    )

    if not front_exists or not side_exists:
        print(f"""
  [FIX] Expected devices not found.
  Current config:
      CAMERA_FRONT_INDEX = {config.CAMERA_FRONT_INDEX}  → looks for /dev/video{config.CAMERA_FRONT_INDEX}
      CAMERA_SIDE_INDEX  = {config.CAMERA_SIDE_INDEX}  → looks for /dev/video{config.CAMERA_SIDE_INDEX}

  Update these values in config.py to match what you see above.
        """)
        return False

    return front_exists and side_exists


# ─────────────────────────────────────────────
# STAGE 2 — OPENCV OPEN TEST
# Confirms OpenCV can open both cameras.
# ─────────────────────────────────────────────

def test_opencv_open():
    banner("STAGE 2 — OpenCV camera open test")

    print("""
  What this does:
    Uses OpenCV to open both cameras and read their properties.
    Confirms resolution and FPS match config.py settings.
    """)

    passed = True

    for label, index in [
        ("Front camera", config.CAMERA_FRONT_INDEX),
        ("Side camera",  config.CAMERA_SIDE_INDEX)
    ]:
        print(f"\n  Testing {label} (index {index})...")

        # Try to open the camera
        cam = cv2.VideoCapture(index)

        if not cam.isOpened():
            result(f"{label} opened", False,
                   f"cv2.VideoCapture({index}) failed")
            print(f"""
  [FIX] OpenCV cannot open camera at index {index}.
  The device exists but OpenCV can't access it.
  Try: sudo usermod -a -G video fieldsight
  Then log out and back in, and retry.
            """)
            passed = False
            continue

        result(f"{label} opened", True)

        # Set and read back resolution
        cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cam.set(cv2.CAP_PROP_FPS,          config.CAMERA_FPS)

        actual_w   = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(cam.get(cv2.CAP_PROP_FPS))

        print(f"    Resolution: {actual_w}x{actual_h} "
              f"(config wants {config.CAMERA_WIDTH}x{config.CAMERA_HEIGHT})")
        print(f"    FPS: {actual_fps} (config wants {config.CAMERA_FPS})")

        # Some cameras don't support 1280x720 — note it but don't fail
        if actual_w != config.CAMERA_WIDTH or actual_h != config.CAMERA_HEIGHT:
            print(f"  [NOTE] Camera returned different resolution than requested.")
            print(f"  This is normal — some cameras have fixed resolutions.")
            print(f"  Update CAMERA_WIDTH/HEIGHT in config.py to match actual.")

        cam.release()

    return passed


# ─────────────────────────────────────────────
# STAGE 3 — SINGLE CAPTURE TEST
# Captures one frame from each camera individually.
# ─────────────────────────────────────────────

def test_single_capture():
    banner("STAGE 3 — Single frame capture test")

    print("""
  What this does:
    Captures one frame from each camera and saves it to disk.
    Point each camera at something visible so you can check the image.

  What to look for:
    Image files appear in the captured_images/ folder.
    Images show what the camera is pointed at (not black, not corrupt).
    """)

    prompt("Point both cameras at something visible.")

    # Make sure save directory exists
    os.makedirs(config.CAMERA_SAVE_DIR, exist_ok=True)

    passed = True

    for label, index in [
        ("front", config.CAMERA_FRONT_INDEX),
        ("side",  config.CAMERA_SIDE_INDEX)
    ]:
        cam = cv2.VideoCapture(index)

        if not cam.isOpened():
            result(f"{label} camera capture", False, "cannot open camera")
            passed = False
            continue

        # Configure camera
        cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        # Warm up — discard first few frames
        # USB cameras often return dark frames immediately after opening
        for _ in range(3):
            cam.read()

        # Capture real frame
        ret, frame = cam.read()
        cam.release()

        if not ret or frame is None:
            result(f"{label} camera capture", False, "frame read failed")
            passed = False
            continue

        # Save to disk
        timestamp = int(time.time() * 1000)
        filename  = f"test_{label}_{timestamp}.jpg"
        filepath  = os.path.join(config.CAMERA_SAVE_DIR, filename)

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.CAMERA_JPEG_QUALITY]
        save_ok = cv2.imwrite(filepath, frame, encode_params)

        if not save_ok:
            result(f"{label} camera save", False, f"imwrite failed for {filepath}")
            passed = False
            continue

        # Check file actually exists and has size > 0
        file_size = os.path.getsize(filepath)
        result(
            f"{label} camera capture + save",
            file_size > 0,
            f"saved to {filepath} ({file_size} bytes)"
        )

        if file_size == 0:
            passed = False

    if passed:
        print(f"\n  Images saved to {config.CAMERA_SAVE_DIR}/")
        print(f"  View them with: ls -la {config.CAMERA_SAVE_DIR}/")

    return passed


# ─────────────────────────────────────────────
# STAGE 4 — BOTH CAMERAS CAPTURE
# Captures from both cameras back to back.
# Simulates what state_machine.py does at each scan point.
# ─────────────────────────────────────────────

def test_both_capture():
    banner("STAGE 4 — Both cameras capture test")

    print("""
  What this does:
    Captures from both cameras back to back.
    This simulates what happens at each scan point during a real run.
    Checks timing — both captures should complete in under 2 seconds.
    """)

    prompt("Both cameras pointed at something visible.")

    os.makedirs(config.CAMERA_SAVE_DIR, exist_ok=True)

    start_time = time.time()
    paths = []
    passed = True

    for label, index in [
        ("front", config.CAMERA_FRONT_INDEX),
        ("side",  config.CAMERA_SIDE_INDEX)
    ]:
        cam = cv2.VideoCapture(index)

        if not cam.isOpened():
            result(f"{label} open", False)
            passed = False
            continue

        cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        for _ in range(3):
            cam.read()

        ret, frame = cam.read()
        cam.release()

        if not ret or frame is None:
            result(f"{label} capture", False)
            passed = False
            continue

        timestamp = int(time.time() * 1000)
        filename  = f"test_both_{label}_{timestamp}.jpg"
        filepath  = os.path.join(config.CAMERA_SAVE_DIR, filename)
        cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, config.CAMERA_JPEG_QUALITY])
        paths.append(filepath)

    elapsed = time.time() - start_time

    result("Both cameras captured", passed and len(paths) == 2)
    result(
        f"Capture time under 2 seconds",
        elapsed < 2.0,
        f"took {elapsed:.2f}s"
    )

    if elapsed >= 2.0:
        print("""
  [NOTE] Both captures took over 2 seconds.
  This is ok but means the rover will be paused longer at each scan point.
  Consider reducing CAMERA_FPS or CAMERA_WIDTH in config.py.
        """)

    return passed


# ─────────────────────────────────────────────
# STAGE 5 — CAMERA MODULE IMPORT TEST
# Confirms camera.py itself can be imported and used.
# ─────────────────────────────────────────────

def test_module_import():
    banner("STAGE 5 — camera.py module import test")

    print("""
  What this does:
    Imports CameraController from camera.py and runs a full capture.
    This confirms the actual module works, not just the raw OpenCV calls.
    """)

    try:
        from modules.camera import CameraController
        result("Import CameraController from modules.camera", True)
    except ImportError as e:
        result("Import CameraController", False, str(e))
        print("  Make sure camera.py is in the modules/ folder.")
        return False

    try:
        camera = CameraController()
        camera.open()
        result("CameraController.open()", True)
    except Exception as e:
        result("CameraController.open()", False, str(e))
        return False

    try:
        front_path, side_path = camera.capture_both()
        result(
            "CameraController.capture_both()",
            True,
            f"front={front_path}  side={side_path}"
        )
    except Exception as e:
        result("CameraController.capture_both()", False, str(e))
        camera.close()
        return False

    camera.close()
    result("CameraController.close()", True)
    return True


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    banner("FieldSight — Camera Hardware Test")

    print("""
  Run stages in order for first-time setup:
    Stage 1 — confirm Pi sees cameras at /dev/video*
    Stage 2 — confirm OpenCV can open both cameras
    Stage 3 — capture single frame from each camera
    Stage 4 — capture from both cameras together
    Stage 5 — confirm camera.py module works end to end
    """)

    print("  Choose a stage:")
    print("    1 — Device scan")
    print("    2 — OpenCV open test")
    print("    3 — Single frame capture")
    print("    4 — Both cameras capture")
    print("    5 — camera.py module import test")
    print("    a — Run all stages in order")

    choice = input("\n  Enter choice [1/2/3/4/5/a]: ").strip().lower()
    print()

    results = {}

    if choice in ("1", "a"):
        results["stage1"] = test_device_scan()

    if choice in ("2", "a"):
        results["stage2"] = test_opencv_open()

    if choice in ("3", "a"):
        results["stage3"] = test_single_capture()

    if choice in ("4", "a"):
        results["stage4"] = test_both_capture()

    if choice in ("5", "a"):
        results["stage5"] = test_module_import()

    banner("TEST SUMMARY")
    labels = {
        "stage1": "Stage 1 — Device scan",
        "stage2": "Stage 2 — OpenCV open",
        "stage3": "Stage 3 — Single capture",
        "stage4": "Stage 4 — Both cameras",
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
        print("  All stages passed. camera.py is ready to use.")
    else:
        print("  Some stages failed — fix issues above before using camera.py.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Test interrupted.\n")
        sys.exit(0)