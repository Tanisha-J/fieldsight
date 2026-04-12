"""
modules/camera.py - FieldSight Camera Controller
=================================================
Manages both USB cameras on the FieldSight rover.

This module is imported by state_machine.py to capture images
of tomato crops as the rover drives down each row.

Hardware layout:
    Left camera  — mounted on left side of rover, points at left crop row
    Right camera — mounted on right side of rover, points at right crop row
    Both cameras are at 8.4" height from ground — confirmed for 6-10" plants.

Usage:
    from modules.camera import CameraController

    camera = CameraController()
    camera.open()

    left_path  = camera.capture_left()    # capture from left camera
    right_path = camera.capture_right()   # capture from right camera
    both_paths = camera.capture_both()    # capture from both at once

    camera.close()

Hardware:
    Both cameras connect via USB directly to the Pi.
    They appear as /dev/video0, /dev/video1, etc.

    Run this on the Pi to confirm indexes:
        ls /dev/video*
        v4l2-ctl --list-devices

    If indexes are wrong, update CAMERA_LEFT_INDEX and
    CAMERA_RIGHT_INDEX in config.py — nothing here needs to change.

Image storage:
    Captured images are saved to CAMERA_SAVE_DIR (from config.py).
    Filenames include a timestamp so they never overwrite each other.
    backend_client.py reads from this folder to send images to the backend.
"""

import os
import time
import cv2       # OpenCV — handles camera access and image processing
import config


class CameraController:
    """
    Controls both USB cameras on the FieldSight rover.

    Handles opening cameras, capturing frames, saving images locally,
    and closing cameras cleanly on shutdown.

    Example:
        camera = CameraController()
        camera.open()

        # Capture from both cameras at each scan point
        left_path, right_path = camera.capture_both()

        camera.close()
    """

    def __init__(self):
        """
        Sets up the camera controller.
        Does NOT open cameras yet — call open() after creating the object.
        """
        # Camera objects — None until open() is called
        self.left_cam  = None
        self.right_cam = None

        # Make sure the save directory exists
        # This is where images get stored on the Pi before upload
        os.makedirs(config.CAMERA_SAVE_DIR, exist_ok=True)

        # Track whether cameras are open
        self._open = False

    # ─────────────────────────────────────────────
    # SETUP AND TEARDOWN
    # ─────────────────────────────────────────────

    def open(self):
        """
        Opens both USB cameras and configures resolution and FPS.
        Call this once when the rover starts up before capturing any images.

        Raises:
            RuntimeError: if either camera fails to open
                          (wrong index, camera not plugged in, etc.)
        """
        # Open left camera using index from config
        # cv2.VideoCapture(index) opens a USB camera by its device index
        self.left_cam = cv2.VideoCapture(config.CAMERA_LEFT_INDEX)

        if not self.left_cam.isOpened():
            raise RuntimeError(
                f"Cannot open left camera at index {config.CAMERA_LEFT_INDEX}. "
                f"Check that camera is plugged in and run 'ls /dev/video*' on the Pi "
                f"to confirm the correct index. Update CAMERA_LEFT_INDEX in config.py."
            )

        # Open right camera
        self.right_cam = cv2.VideoCapture(config.CAMERA_RIGHT_INDEX)

        if not self.right_cam.isOpened():
            raise RuntimeError(
                f"Cannot open right camera at index {config.CAMERA_RIGHT_INDEX}. "
                f"Check that camera is plugged in and run 'ls /dev/video*' on the Pi "
                f"to confirm the correct index. Update CAMERA_RIGHT_INDEX in config.py."
            )

        # Configure resolution and FPS for both cameras
        # These values come from config.py
        for cam in [self.left_cam, self.right_cam]:
            cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            cam.set(cv2.CAP_PROP_FPS,          config.CAMERA_FPS)

        self._open = True

    def close(self):
        """
        Releases both cameras and frees their resources.
        Always call this when the rover is shutting down.
        main.py should call this in its finally block.
        """
        if self.left_cam is not None:
            self.left_cam.release()

        if self.right_cam is not None:
            self.right_cam.release()

        self._open = False

    # ─────────────────────────────────────────────
    # IMAGE CAPTURE
    # ─────────────────────────────────────────────

    def capture_left(self):
        """
        Captures a single frame from the left-facing camera.
        Saves it as a JPEG to the CAMERA_SAVE_DIR folder.

        Returns:
            str — full file path of the saved image
                  e.g. "captured_images/left_1711234567890.jpg"

        Raises:
            RuntimeError: if cameras aren't open or capture fails
        """
        return self._capture(self.left_cam, "left")

    def capture_right(self):
        """
        Captures a single frame from the right-facing camera.
        Saves it as a JPEG to the CAMERA_SAVE_DIR folder.

        Returns:
            str — full file path of the saved image
                  e.g. "captured_images/right_1711234567890.jpg"

        Raises:
            RuntimeError: if cameras aren't open or capture fails
        """
        return self._capture(self.right_cam, "right")

    def capture_both(self):
        """
        Captures from both cameras at each scan point.
        Left camera captures the left crop row.
        Right camera captures the right crop row.
        Called by state_machine.py at every capture point.

        Returns:
            tuple — (left_image_path, right_image_path)

        Example:
            left_path, right_path = camera.capture_both()
            # send both paths to backend_client.py for analysis
        """
        left_path  = self.capture_left()
        right_path = self.capture_right()
        return left_path, right_path

    def _capture(self, cam, label):
        """
        Internal method that handles the actual frame capture and save.
        Used by capture_left() and capture_right().

        Parameters:
            cam   : the cv2.VideoCapture object to read from
            label : string label for the filename ('left' or 'right')

        Returns:
            str — full path to the saved image file

        Raises:
            RuntimeError: if cameras not open, or frame read fails
        """
        if not self._open:
            raise RuntimeError(
                "Cameras are not open. Call camera.open() first."
            )

        # Warm up the camera by reading a few throwaway frames
        # Some USB cameras return dark or blurry frames on first read
        # after being idle — discarding the first few fixes this
        for _ in range(3):
            cam.read()

        # Capture the actual frame
        # ret = True if successful, frame = the image as a numpy array
        ret, frame = cam.read()

        if not ret or frame is None:
            raise RuntimeError(
                f"Failed to capture frame from {label} camera. "
                f"Camera may have disconnected."
            )

        # Build filename with timestamp so files never overwrite each other
        # e.g. "captured_images/left_1711234567890.jpg"
        timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
        filename  = f"{label}_{timestamp}.jpg"
        filepath  = os.path.join(config.CAMERA_SAVE_DIR, filename)

        # Save as JPEG with quality setting from config
        # cv2.IMWRITE_JPEG_QUALITY controls compression (85 = good balance)
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

    def is_open(self):
        """
        Returns True if both cameras are open and ready.
        state_machine.py can check this before starting a scan.
        """
        return (
            self._open
            and self.left_cam is not None
            and self.left_cam.isOpened()
            and self.right_cam is not None
            and self.right_cam.isOpened()
        )

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
            # Only delete image files not any other files
            if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                filepath = os.path.join(config.CAMERA_SAVE_DIR, filename)
                os.remove(filepath)
                deleted += 1

        return deleted