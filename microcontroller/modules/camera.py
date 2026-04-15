"""
modules/camera.py - FieldSight Camera Controller
=================================================
Manages right and left USB cameras on the rover.

* module called on by state_machine.py to capture images

Hardware layout:
    Left camera  — mounted on left side of rover, points at left crop row
    Right camera — mounted on right side of rover, points at right crop row
    Both cameras are at around 8" from ground — plants at around 9".

Debugging notes after testing camera:
    When both cameras are opened simultaneously they compete for USB bandwidth and
    the second camera was timing out. Solution was to open, capture, and close
    each camera sequentially instead of both open at same time.

    Tested and confirmed working on the Pi with both cameras connected!!!!

how to use:
    from modules.camera import CameraController

    camera = CameraController()
    left_path, right_path = camera.capture_both()

Image pathways:
    Captured images are saved to CAMERA_SAVE_DIR (from config.py).
    Filenames include a timestamp so they never overwrite each other.
    backend_client.py reads from this folder to send images to the backend.
"""

import os
import time
import cv2
import config


class CameraController:
    """
    Opens each camera only when capturing, then closes it immediately
    Example:
        camera = CameraController()

        # Capture from both cameras at each decided point
        left_path, right_path = camera.capture_both()

        # dont need open() or close() 
    """

    def __init__(self):
        """
        Sets up the camera controller.
        Creates the save directory if it doesn't exist.
        No cameras are opened during this part of code.
        """
        #confirmed existence of save directory 
        os.makedirs(config.CAMERA_SAVE_DIR, exist_ok=True)


    # IMAGE CAPTURE
    # Each method opens the camera, captures, saves, and closes.

    def capture_left(self):
        """
        Opens the left camera, captures one frame, saves it, closes camera.

        Returns:
            str — full file path of the saved image

        Raises:
            RuntimeError: if camera cannot be opened or frame read fails
        #both tested and working
        """
        return self._capture_single(config.CAMERA_LEFT_INDEX, "left")

    def capture_right(self):
        """
        Opens the right camera, captures one frame, saves it, closes camera.

        Returns:
            str — full file path of the saved image

        Raises:
            RuntimeError: if camera cannot be opened or frame read fails
        """
        return self._capture_single(config.CAMERA_RIGHT_INDEX, "right")

    def capture_both(self):
        """
        Captures from left camera then right camera sequentially.
        Called by state_machine.py at each of the four scan points

        Returns:
            tuple — (left_image_path, right_image_path)

        Example:
            left_path, right_path = camera.capture_both()
            # send both paths to backend_client.py for analysis
        """
        left_path  = self.capture_left()
        right_path = self.capture_right()
        return left_path, right_path

    def _capture_single(self, index, label):
        """
        Internal method — opens one camera, captures a frame, closes it.

        Parameters:
            index : USB video device index (from config.py)
            label : string label for filename ('left' or 'right')

        Returns:
            str — full path to the saved image file

        Raises:
            RuntimeError: if camera can't open or frame read fails
        """
        # Open the camera
        cam = cv2.VideoCapture(index)

        if not cam.isOpened():
            raise RuntimeError(
                f"Cannot open {label} camera at index {index}. "
                f"Check that camera is plugged in and run 'ls /dev/video*' "
                f"to confirm the correct index. "
                f"Update CAMERA_LEFT_INDEX or CAMERA_RIGHT_INDEX in config.py."
            )

        # Set resolution
        cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        # Allow camera to initialize — USB cameras need a moment
        # after opening before they return valid frames
        time.sleep(1.0)

        # Capture the frame
        ret, frame = cam.read()

        # Close camera immediately after capture
        # This releases USB bandwidth for the next camera
        cam.release()

        if not ret or frame is None:
            raise RuntimeError(
                f"Failed to capture frame from {label} camera at index {index}. "
                f"Camera may have disconnected."
            )

        # Build filename with timestamp so files never overwrite each other
        timestamp = int(time.time() * 1000)
        filename  = f"{label}_{timestamp}.jpg"
        filepath  = os.path.join(config.CAMERA_SAVE_DIR, filename)

        # Save as JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.CAMERA_JPEG_QUALITY]
        success = cv2.imwrite(filepath, frame, encode_params)

        if not success:
            raise RuntimeError(
                f"Failed to save image to {filepath}. "
                f"Check that {config.CAMERA_SAVE_DIR} folder exists "
                f"and Pi has write permissions."
            )

        return filepath

    # ─────────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────────

    def cameras_available(self):
        """
        Checks if both cameras are physically available.
        state_machine.py can call this before starting a scan.

        Returns:
            bool — True if both cameras can be opened
        """
        for index, label in [
            (config.CAMERA_LEFT_INDEX,  "left"),
            (config.CAMERA_RIGHT_INDEX, "right")
        ]:
            cam = cv2.VideoCapture(index)
            available = cam.isOpened()
            cam.release()
            if not available:
                return False
        return True

    def get_save_dir(self):
        """
        Returns the folder path where captured images are saved.
        backend_client.py uses this to find images to upload.
        """
        return config.CAMERA_SAVE_DIR

    def clear_saved_images(self):
        """
        Deletes all saved images from the local folder.
        Call this after backend_client.py has successfully
        uploaded all images from a completed scan session.
        Prevents the Pi's SD card from filling up over time.
        """
        deleted = 0
        for filename in os.listdir(config.CAMERA_SAVE_DIR):
            if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                filepath = os.path.join(config.CAMERA_SAVE_DIR, filename)
                os.remove(filepath)
                deleted += 1
        return deleted