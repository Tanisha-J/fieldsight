"""
modules/imu.py - FieldSight IMU (MPU6050) Controller
=====================================================
Reads accelerometer, gyroscope, and temperature data from the
MPU6050 sensor over I2C.

This module is imported by state_machine.py to track rover heading
and detect when the rover has completed a turn.

Usage:
    from modules.imu import IMU

    imu = IMU()
    imu.wake()

    data = imu.read_all()
    print(data['heading_rate'])  # degrees per second — how fast rover is turning
    print(data['temp_c'])        # temperature in celsius

    imu.close()

Hardware mounting notes (confirmed during hardware testing):
    The MPU6050 is mounted sideways on this rover.
    This means the axes are rotated from their default orientation:

        Gravity axis     → Ax  (reads ≈ -0.9g at rest, not Az)
        Pitch fwd/back   → Ay  (goes negative tilting forward)
        Roll left/right  → Az
        Yaw / turning    → Gx  ← most important, tracks rover heading
        Gyro X drift     → ≈ -6.2 °/s at rest (offset applied automatically)

    If the IMU is remounted, rerun tests/test_imu.py Stage 4
    to find the new axis mapping and update HEADING_AXIS and
    GYRO_DRIFT_OFFSET below.

I2C connection:
    SDA → GPIO2 (physical pin 3)
    SCL → GPIO3 (physical pin 5)
    VCC → 3.3V  (physical pin 1)
    GND → any GND pin
"""

import time
import smbus2
import config


# ─────────────────────────────────────────────
# MPU6050 REGISTER ADDRESSES
# These are the memory addresses inside the chip we read/write to.
# From the MPU6050 datasheet.
# ─────────────────────────────────────────────

REG_PWR_MGMT_1   = 0x6B  # power management — write 0x00 to wake from sleep
REG_WHO_AM_I     = 0x75  # identity check — reading returns 0x68
REG_ACCEL_XOUT_H = 0x3B  # start of accel data (6 bytes: X_H X_L Y_H Y_L Z_H Z_L)
REG_GYRO_XOUT_H  = 0x43  # start of gyro data  (6 bytes: same format)
REG_TEMP_OUT_H   = 0x41  # start of temp data  (2 bytes: high, low)

# ─────────────────────────────────────────────
# SCALE FACTORS
# Converts raw 16-bit integers to real physical units.
# These match the MPU6050 default configuration (no custom range set).
# ─────────────────────────────────────────────

ACCEL_SCALE = 16384.0  # raw units per 1g     at ±2g  full scale range
GYRO_SCALE  = 131.0    # raw units per 1 °/s  at ±250°/s full scale range

# ─────────────────────────────────────────────
# MOUNTING CALIBRATION
# Found during hardware testing with test_imu.py Stage 4.
# These values are specific to how the IMU is physically mounted
# on this rover. If remounted, rerun Stage 4 and update these.
# ─────────────────────────────────────────────

# Which raw axis corresponds to the rover turning left/right
# 'gx' = Gx responds to yaw (spinning) based on our hardware test
HEADING_AXIS = 'gx'

# Gyro drift offset — the gyro reads this value even when completely still
# Subtract this from every Gx reading to get accurate rotation rate
# Measured during test_imu.py Stage 3 (averaged over 20 samples at rest)
GYRO_DRIFT_OFFSET = -6.2   # degrees per second


class IMU:
    """
    Interface to the MPU6050 IMU sensor over I2C.

    Provides accelerometer, gyroscope, and temperature readings.
    Automatically applies the axis remapping and drift correction
    based on how the sensor is mounted on this rover.

    Example:
        imu = IMU()
        imu.wake()

        while True:
            data = imu.read_all()
            print(f"Heading rate: {data['heading_rate']:.1f} °/s")
            time.sleep(0.1)

        imu.close()
    """

    def __init__(self):
        """
        Opens the I2C bus and stores the IMU address from config.
        Does NOT wake the chip — call wake() after creating the object.

        Raises:
            OSError: if the I2C bus cannot be opened (I2C not enabled
                     on Pi, or hardware not connected)
        """
        # SMBus(1) opens I2C bus 1 — the standard bus on the Pi GPIO header
        # (SDA=GPIO2, SCL=GPIO3)
        try:
            self.bus  = smbus2.SMBus(1)
            self.addr = config.IMU_I2C_ADDRESS  # 0x68 from config.py
        except Exception as e:
            raise OSError(
                f"Cannot open I2C bus. Make sure I2C is enabled "
                f"(sudo raspi-config → Interface Options → I2C). Error: {e}"
            )

        # Track whether the chip has been woken up
        self._awake = False

    # ─────────────────────────────────────────────
    # SETUP
    # ─────────────────────────────────────────────

    def wake(self):
        """
        Wakes the MPU6050 from sleep mode.

        The chip starts in sleep mode by default every time it powers on.
        Nothing will work until you call this. Always call it right after
        creating the IMU object.

        Raises:
            OSError: if the chip is not responding (wiring issue)
        """
        # Verify the chip is actually there before trying to wake it
        who = self.bus.read_byte_data(self.addr, REG_WHO_AM_I)
        if who != 0x68:
            raise OSError(
                f"MPU6050 not found at address 0x{self.addr:02X}. "
                f"WHO_AM_I returned 0x{who:02X} (expected 0x68). "
                f"Check wiring: SDA→GPIO2, SCL→GPIO3, VCC→3.3V."
            )

        # Write 0x00 to PWR_MGMT_1 to wake the chip from sleep
        self.bus.write_byte_data(self.addr, REG_PWR_MGMT_1, 0x00)

        # Small delay to let the chip finish waking up
        time.sleep(0.1)

        self._awake = True

    def close(self):
        """
        Closes the I2C bus connection.
        Call this when the rover is shutting down.
        main.py should call this in its finally block.
        """
        self.bus.close()
        self._awake = False

    # ─────────────────────────────────────────────
    # RAW READS
    # Low level register reads — return raw 16-bit integers
    # ─────────────────────────────────────────────

    def _read_raw_accel(self):
        """
        Reads all 3 accel axes as raw 16-bit signed integers.
        Returns (ax_raw, ay_raw, az_raw).
        """
        data = self.bus.read_i2c_block_data(self.addr, REG_ACCEL_XOUT_H, 6)
        return (
            self._to_signed(data[0], data[1]),  # X axis
            self._to_signed(data[2], data[3]),  # Y axis
            self._to_signed(data[4], data[5])   # Z axis
        )

    def _read_raw_gyro(self):
        """
        Reads all 3 gyro axes as raw 16-bit signed integers.
        Returns (gx_raw, gy_raw, gz_raw).
        """
        data = self.bus.read_i2c_block_data(self.addr, REG_GYRO_XOUT_H, 6)
        return (
            self._to_signed(data[0], data[1]),  # X axis
            self._to_signed(data[2], data[3]),  # Y axis
            self._to_signed(data[4], data[5])   # Z axis
        )

    def _read_raw_temp(self):
        """
        Reads the temperature register as a raw 16-bit signed integer.
        """
        high = self.bus.read_byte_data(self.addr, REG_TEMP_OUT_H)
        low  = self.bus.read_byte_data(self.addr, REG_TEMP_OUT_H + 1)
        return self._to_signed(high, low)

    @staticmethod
    def _to_signed(high_byte, low_byte):
        """
        Combines two bytes into a signed 16-bit integer.
        The MPU6050 stores each reading as two bytes (high and low).
        Handles negative numbers using two's complement.

        Example:
            high=0x00, low=0x64 → 100   (positive)
            high=0xFF, low=0x9C → -100  (negative)
        """
        value = (high_byte << 8) | low_byte  # combine into 16-bit number
        if value >= 0x8000:                   # if top bit set, it's negative
            value -= 0x10000
        return value

    # ─────────────────────────────────────────────
    # SCALED READS
    # Convert raw integers to real physical units
    # ─────────────────────────────────────────────

    def read_accel(self):
        """
        Reads accelerometer and returns values in g (gravitational units).
        1g = 9.8 m/s². At rest, one axis will read ≈ ±1g (gravity).

        Returns:
            dict with keys: ax, ay, az (all in g)

        Note:
            On this rover the IMU is mounted sideways so ax ≈ -0.9g at rest.
            This is expected — see mounting notes at top of file.
        """
        ax_r, ay_r, az_r = self._read_raw_accel()
        return {
            'ax': ax_r / ACCEL_SCALE,
            'ay': ay_r / ACCEL_SCALE,
            'az': az_r / ACCEL_SCALE
        }

    def read_gyro(self):
        """
        Reads gyroscope and returns values in degrees per second (°/s).
        Positive = rotating one way, negative = rotating the other.
        At rest all values should be close to 0 after drift correction.

        Returns:
            dict with keys: gx, gy, gz (all in °/s, drift corrected)

        Note:
            Gx is the heading axis on this rover (confirmed in hardware test).
            Drift offset of -6.2 °/s is automatically subtracted from Gx.
        """
        gx_r, gy_r, gz_r = self._read_raw_gyro()

        # Convert raw to degrees per second
        gx = gx_r / GYRO_SCALE
        gy = gy_r / GYRO_SCALE
        gz = gz_r / GYRO_SCALE

        # Subtract drift offset from heading axis so it reads ~0 when still
        # Without this correction the heading would drift even when not moving
        gx -= GYRO_DRIFT_OFFSET

        return {'gx': gx, 'gy': gy, 'gz': gz}

    def read_temp(self):
        """
        Reads the chip temperature in degrees Celsius.
        This is the temperature of the MPU6050 chip itself, not ambient.
        Useful for monitoring if the chip is getting too hot.

        Returns:
            float — temperature in Celsius
        """
        raw = self._read_raw_temp()
        # Formula from MPU6050 datasheet
        return (raw / 340.0) + 36.53

    def read_all(self):
        """
        Reads accel, gyro, and temperature in a single call.
        This is the main method state_machine.py uses.

        Returns:
            dict with keys:
                ax, ay, az       — acceleration in g
                gx, gy, gz       — rotation rate in °/s (drift corrected)
                heading_rate     — rotation rate on the yaw axis (°/s)
                                   positive = turning right
                                   negative = turning left
                temp_c           — chip temperature in Celsius

        Example:
            data = imu.read_all()
            if abs(data['heading_rate']) > 5:
                print('Rover is turning')
        """
        accel = self.read_accel()
        gyro  = self.read_gyro()
        temp  = self.read_temp()

        return {
            # Raw accel axes
            'ax': accel['ax'],
            'ay': accel['ay'],
            'az': accel['az'],

            # Raw gyro axes (drift corrected)
            'gx': gyro['gx'],
            'gy': gyro['gy'],
            'gz': gyro['gz'],

            # Heading rate — the axis that responds to the rover turning
            # Based on hardware test: Gx is the yaw axis on this rover
            # Positive = turning right, negative = turning left
            'heading_rate': gyro[HEADING_AXIS],

            # Chip temperature
            'temp_c': temp
        }

    # ─────────────────────────────────────────────
    # HEADING TRACKING
    # Integrates gyro readings over time to estimate
    # how many degrees the rover has turned.
    # Used by state_machine.py for row-end turns.
    # ─────────────────────────────────────────────

    def measure_turn(self, target_degrees, timeout=10.0):
        """
        Blocks until the rover has turned approximately target_degrees,
        or until timeout is reached.

        This is called by state_machine.py when the rover needs to turn
        90 degrees at the end of a crop row. It integrates the gyro
        reading over time to estimate total rotation.

        Parameters:
            target_degrees : how many degrees to turn (positive = right, negative = left)
            timeout        : max seconds to wait before giving up (default 10s)

        Returns:
            float — actual degrees turned (may differ slightly from target)

        Example:
            # Turn right 90 degrees
            actual = imu.measure_turn(90)
            print(f'Turned {actual:.1f} degrees')

        Note:
            Gyro integration has drift — this is accurate enough for
            90 degree row turns but not for precise navigation.
            For better accuracy, consider adding a magnetometer later.
        """
        degrees_turned = 0.0
        last_time      = time.time()
        start_time     = time.time()

        while abs(degrees_turned) < abs(target_degrees):
            # Check timeout — stop if taking too long
            if time.time() - start_time > timeout:
                break

            # Read current rotation rate on heading axis
            gyro        = self.read_gyro()
            rate        = gyro[HEADING_AXIS]  # °/s

            # Calculate time since last reading
            now         = time.time()
            dt          = now - last_time     # seconds elapsed
            last_time   = now

            # Integrate: degrees = rate × time
            # This accumulates small angle changes into total rotation
            degrees_turned += rate * dt

            # Small delay to avoid hammering the I2C bus
            time.sleep(0.01)

        return degrees_turned

    def is_level(self, threshold=0.3):
        """
        Returns True if the rover is on roughly flat ground.
        Used by state_machine.py to detect if the rover has tipped
        or is on a steep slope.

        Parameters:
            threshold : how many g of tilt to allow before flagging (default 0.3g)

        Returns:
            bool — True if level, False if tilted beyond threshold

        Example:
            if not imu.is_level():
                motors.stop()
                print('Rover tilted — stopping for safety')
        """
        accel = self.read_accel()

        # On this rover gravity shows up on Ax (mounted sideways)
        # Ay and Az should both be near 0 when level
        # If either exceeds threshold, rover is tilted
        ay_tilt = abs(accel['ay'])
        az_tilt = abs(accel['az'])

        return ay_tilt < threshold and az_tilt < threshold