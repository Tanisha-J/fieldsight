"""
modules/gps.py - FieldSight GPS Controller
==========================================
Reads location data from the VK-162 USB GPS module.

This module is imported by state_machine.py to get the rover's
current coordinates at each scan point. Those coordinates get
attached to every scan result so the frontend can place pins
on the Mapbox map showing exactly where disease was detected.

Usage:
    from modules.gps import GPS

    gps = GPS()
    gps.open()

    location = gps.get_location()
    if location:
        print(f"Lat: {location['lat']}, Lng: {location['lng']}")
    else:
        print("No GPS fix yet")

    gps.close()

Hardware:
    VK-162 USB GPS plugs directly into Pi USB port.
    Appears as a serial device — usually /dev/ttyUSB0.

    Run this on the Pi to confirm:
        ls /dev/ttyUSB*

    If port is wrong, update GPS_PORT in config.py.
    Nothing in this file needs to change.

Important notes:
    - GPS needs to be outdoors to get a satellite fix
    - First fix after power-on takes 30-60 seconds (cold start)
    - Subsequent fixes are faster (warm start)
    - Indoors you will get no fix — get_location() returns None
    - Always check if location is None before using coordinates
"""

import serial        # pyserial — handles USB serial communication
import pynmea2       # parses NMEA sentences from GPS module
import threading     # runs GPS reading in background thread
import time
import config


class GPS:
    """
    Interface to the VK-162 USB GPS module over serial.

    Reads NMEA sentences from the GPS in a background thread
    and stores the latest valid coordinates. state_machine.py
    calls get_location() to get the current position.

    The background thread approach means the GPS is always
    reading in the background — get_location() just returns
    whatever the latest fix was. This is better than reading
    on demand because serial reads can block for up to GPS_TIMEOUT
    seconds if no data is coming in.

    Example:
        gps = GPS()
        gps.open()

        # Wait for first fix
        while not gps.has_fix():
            print("Waiting for GPS fix...")
            time.sleep(1)

        location = gps.get_location()
        print(f"Position: {location['lat']}, {location['lng']}")

        gps.close()
    """

    def __init__(self):
        """
        Sets up the GPS controller.
        Does NOT open the serial port — call open() after creating the object.
        """
        # Serial port object — None until open() is called
        self._serial = None

        # Latest GPS fix — None until first valid reading
        # Stored as a dict: {'lat': float, 'lng': float, 'timestamp': str}
        self._latest = None

        # Background thread that continuously reads from GPS
        self._thread  = None
        self._running = False

        # Lock prevents the main thread and background thread from
        # reading/writing _latest at the same time (thread safety)
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────
    # SETUP AND TEARDOWN
    # ─────────────────────────────────────────────

    def open(self):
        """
        Opens the serial connection to the GPS module and starts
        the background reading thread.

        Call this once when the rover starts up.

        Raises:
            serial.SerialException: if GPS port not found
                (wrong port, GPS not plugged in)
        """
        try:
            self._serial = serial.Serial(
                port     = config.GPS_PORT,      # /dev/ttyUSB0 from config
                baudrate = config.GPS_BAUDRATE,  # 9600 for VK-162
                timeout  = config.GPS_TIMEOUT    # seconds to wait per read
            )
        except serial.SerialException as e:
            raise serial.SerialException(
                f"Cannot open GPS on {config.GPS_PORT}. "
                f"Check that GPS is plugged in and run 'ls /dev/ttyUSB*' "
                f"to confirm the port. Update GPS_PORT in config.py. "
                f"Error: {e}"
            )

        # Start background thread to continuously read GPS data
        # daemon=True means the thread dies automatically when main program exits
        self._running = True
        self._thread  = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def close(self):
        """
        Stops the background reading thread and closes the serial port.
        Always call this when the rover is shutting down.
        main.py should call this in its finally block.
        """
        self._running = False

        # Wait for background thread to finish
        if self._thread is not None:
            self._thread.join(timeout=2.0)

        # Close serial port
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    # ─────────────────────────────────────────────
    # BACKGROUND READING THREAD
    # Continuously reads NMEA sentences from GPS
    # and updates _latest when a valid fix is found
    # ─────────────────────────────────────────────

    def _read_loop(self):
        """
        Background thread that continuously reads NMEA sentences
        from the GPS serial port and parses them.

        Runs until self._running is set to False by close().

        NMEA sentences look like:
            $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,...
            $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,...

        We parse GPRMC sentences because they contain:
            - latitude and longitude
            - status (A=active/valid, V=void/invalid)
            - timestamp
        """
        while self._running:
            try:
                # Read one line from the GPS serial port
                # Each line is one NMEA sentence ending in \n
                raw_line = self._serial.readline()

                # Decode bytes to string, ignore invalid characters
                line = raw_line.decode('ascii', errors='replace').strip()

                # Skip empty lines
                if not line:
                    continue

                # Only process GPRMC sentences — they have position + validity
                # Other sentence types (GPGGA, GPGSV etc) are ignored
                if not line.startswith('$GPRMC') and not line.startswith('$GNRMC'):
                    continue

                # Parse the NMEA sentence using pynmea2
                msg = pynmea2.parse(line)

                # Check if this is a valid fix
                # status 'A' = Active (valid fix), 'V' = Void (no fix)
                if msg.status != 'A':
                    # No satellite fix yet — keep waiting
                    continue

                # Valid fix — extract coordinates
                # pynmea2 gives us latitude and longitude as decimal degrees
                location = {
                    'lat':       msg.latitude,   # decimal degrees N/S
                    'lng':       msg.longitude,  # decimal degrees E/W
                    'timestamp': str(msg.timestamp)  # UTC time from GPS
                }

                # Update _latest using lock so main thread can safely read it
                with self._lock:
                    self._latest = location

            except pynmea2.ParseError:
                # Malformed NMEA sentence — skip it and keep reading
                # This happens occasionally and is normal
                continue

            except serial.SerialException:
                # Serial port error — GPS may have been unplugged
                # Stop the thread
                break

            except Exception:
                # Any other error — skip and keep reading
                continue

    # ─────────────────────────────────────────────
    # LOCATION ACCESS
    # Called by state_machine.py to get current position
    # ─────────────────────────────────────────────

    def get_location(self):
        """
        Returns the most recent valid GPS coordinates.

        Returns:
            dict with keys:
                lat       — latitude as decimal degrees (float)
                            positive = North, negative = South
                lng       — longitude as decimal degrees (float)
                            positive = East, negative = West
                timestamp — UTC time string from GPS satellite

            None — if no valid fix has been received yet
                   (GPS still searching for satellites)

        Example:
            location = gps.get_location()
            if location is None:
                print("No GPS fix yet — using last known position")
            else:
                print(f"Lat: {location['lat']:.6f}")
                print(f"Lng: {location['lng']:.6f}")
        """
        # Use lock to safely read _latest from main thread
        # while background thread might be writing to it
        with self._lock:
            return self._latest

    def has_fix(self):
        """
        Returns True if the GPS has a valid satellite fix.
        Use this to wait before starting a scan.

        Example:
            print("Waiting for GPS fix...")
            while not gps.has_fix():
                time.sleep(1)
            print("GPS ready")
        """
        with self._lock:
            return self._latest is not None

    def wait_for_fix(self, timeout=120):
        """
        Blocks until GPS gets a valid fix or timeout is reached.
        Called by state_machine.py before starting a scan to make
        sure coordinates will be available.

        Parameters:
            timeout : max seconds to wait for fix (default 120s = 2 minutes)

        Returns:
            bool — True if fix acquired, False if timed out

        Example:
            if not gps.wait_for_fix(timeout=60):
                print("GPS timeout — starting scan without coordinates")
        """
        start = time.time()
        while not self.has_fix():
            if time.time() - start > timeout:
                return False
            time.sleep(1.0)
        return True

    def get_location_or_default(self, default_lat=0.0, default_lng=0.0):
        """
        Returns current GPS coordinates, or default values if no fix.
        Use this when you want to proceed even without a GPS fix
        rather than blocking on wait_for_fix().

        Parameters:
            default_lat : latitude to use if no fix (default 0.0)
            default_lng : longitude to use if no fix (default 0.0)

        Returns:
            dict with lat, lng, timestamp keys

        Example:
            # Use last known position or 0,0 if never had a fix
            location = gps.get_location_or_default()
            send_to_backend(location['lat'], location['lng'])
        """
        location = self.get_location()

        if location is None:
            return {
                'lat':       default_lat,
                'lng':       default_lng,
                'timestamp': 'no_fix'
            }

        return location