"""
config.py

This is the ONLY place where settings and pin numbers live.
Import from here.
    If you want to change anything, change it here once.

use it like this:
    from config import MOTOR_LEFT_IN1, BACKEND_URL
"""

# GPIO PINS — LEFT MOTOR DRIVER (L298N U4)
# Controls Motor 1 (front-left) and Motor 2 (rear-left)

MOTOR_LEFT_IN1 = 6      # GPIO17 → IN1  (Motor 1 direction)
MOTOR_LEFT_IN2 = 5      # GPIO27 → IN2  (Motor 1 direction)
MOTOR_LEFT_IN3 = 20      # GPIO22 → IN3  (Motor 2 direction)
MOTOR_LEFT_IN4 = 16      # GPIO23 → IN4  (Motor 2 direction)
MOTOR_LEFT_ENA = 12      # GPIO18 (PWM0) → ENA  (Motor 1 speed)
MOTOR_LEFT_ENB = 19      # GPIO13 (PWM1) → ENB  (Motor 2 speed)

# GPIO PINS — RIGHT MOTOR DRIVER (L298N U1)
# Controls Motor 3 (front-right) and Motor 4 (rear-right)

MOTOR_RIGHT_IN1 = 17      # GPIO5  → IN1  (Motor 3 direction)
MOTOR_RIGHT_IN2 = 27      # GPIO6  → IN2  (Motor 3 direction)
MOTOR_RIGHT_IN3 = 22     # GPIO16 → IN3  (Motor 4 direction)
MOTOR_RIGHT_IN4 = 23     # GPIO20 → IN4  (Motor 4 direction)
MOTOR_RIGHT_ENA = 18     # GPIO12 (PWM0) → ENA  (Motor 3 speed)
MOTOR_RIGHT_ENB = 13     # GPIO19 (PWM1) → ENB  (Motor 4 speed)

# MOTOR CONSTANTS
# 0.0 = off, 1.0 = full speed
# MAX_PWM
# ex. At 45% PWM on 30 RPM motors with 7" wheels
#   Speed  ≈ 0.28 mph
#   Current ≈ 5–6A average
#   150 ft run ≈ 6 minutes

CRUISE_PWM      = 0.45   # straight line driving
TURN_INNER_PWM  = 0.0   # inside wheels during a curve
TURN_OUTER_PWM  = 0.45   # outside wheels during a curve
MAX_PWM         = 0.60   # max

# step up by RAMP_STEP every RAMP_DELAY_SEC to reduce current spikes.
RAMP_STEP       = 0.05   # PWM increment per step
RAMP_DELAY_SEC  = 0.10   # seconds between ramp steps

# GPIO PINS — IMU (MPU6050)
# I2C 
# Use smbus2: bus = smbus2.SMBus(1), then read registers using bus.read_byte_data() 

IMU_SDA         = 2      # GPIO2 → SDA (I2C data)
IMU_SCL         = 3      # GPIO3 → SCL (I2C clock)
IMU_I2C_ADDRESS = 0x68   # MPU6050 default I2C address (AD0 pin LOW)
                          # If AD0 is pulled HIGH, address becomes 0x69

# CAMERA
# Two USB cameras — one on each side of the rover
# Both point sideways to capture rows on left and right
# Camera height confirmed at 9" from ground — good for 6-10" tomato plants.
# Indexes may shift depending on plug order —
# run `ls /dev/video*` with both cameras plugged in to confirm.
# ─────────────────────────────────────────────
CAMERA_LEFT_INDEX   = 0      # USB index for left-facing camera
CAMERA_RIGHT_INDEX  = 2      # USB index for right-facing camera
                              # recheck with `v4l2-ctl --list-devices` on Pi
CAMERA_WIDTH        = 1280   # capture width in pixels  (720p)
CAMERA_HEIGHT       = 720    # capture height in pixels (720p)
CAMERA_FPS          = 30     # frames per second
CAMERA_JPEG_QUALITY = 85     # JPEG compression quality (0–100)
CAMERA_SAVE_DIR     = "captured_images"  # local folder on Pi before upload

# ─────────────────────────────────────────────
# GPS — VK-162 USB GPS
# Appears as a serial device, not a GPIO pin.
# Run `ls /dev/ttyUSB*` to confirm port — will shift if other USB-serial
# devices (like an Arduino) are also connected.
# ─────────────────────────────────────────────
GPS_PORT        = "/dev/ttyACM0"   # serial port
GPS_BAUDRATE    = 9600             # VK-162 default baud rate
GPS_TIMEOUT     = 1                # seconds before giving up on a read

# ─────────────────────────────────────────────
# BATTERY & POWER (for logging / runtime estimates)
# Battery: 12V 10Ah LiFePO4
# ─────────────────────────────────────────────
BATTERY_VOLTAGE         = 12.0   # volts
BATTERY_CAPACITY_AH     = 10.0   # rated Ah
BATTERY_USABLE_AH       = 8.0    # safe usable Ah (~80% of rated for LiFePO4)
MOTOR_AVG_CURRENT_A     = 5.5    # expected average draw at CRUISE_PWM (all 4 motors)
MOTOR_PEAK_CURRENT_A    = 20.0   # expected peak during turns / acceleration
MOTOR_STALL_CURRENT_A   = 30.0   # worst-case stall (all 4 motors jammed)
# Estimated continuous runtime at cruise: BATTERY_USABLE_AH / MOTOR_AVG_CURRENT_A ≈ 1.45 hrs

# ─────────────────────────────────────────────
# ROVER BEHAVIOR
# ─────────────────────────────────────────────
ROVER_MAX_SPEED_MPH  = 0.62    # top speed at 100% PWM (30 RPM motors, 7" wheels)
ROVER_CRUISE_MPH     = 0.28    # actual cruise speed at CRUISE_PWM (45%)
ROVER_CRUISE_FPS     = 0.41    # feet per second at cruise (0.28 mph × 1.467)


# Field dimensions — confirmed for demo
ROW_LENGTH_IN        = 100.0   # inches — length of each crop row
ROW_LENGTH_FT        = ROW_LENGTH_IN / 12.0   # = 8.33 feet
ROW_SPACING_IN       = 98.0    # inches — distance to travel sideways between rows
ROW_SPACING_FT       = ROW_SPACING_IN / 12.0  # = 8.17 feet
NUM_ROWS             = 2       # number of rows to scan
TURN_ANGLE_DEGREES   = 90      # degrees to turn at end of each row
 
# Capture pattern — 4 stops per row, evenly spaced
CAPTURES_PER_ROW     = 4       # number of photo stops per row
# Distance between each capture point
# Formula: ROW_LENGTH_FT / (CAPTURES_PER_ROW + 1) = 8.33 / 5 = ~1.67 feet
CAPTURE_EVERY_FT     = ROW_LENGTH_FT / (CAPTURES_PER_ROW + 1)
 
SCAN_SETTLE_TIME_SEC = 0.3     # pause after stopping before capturing (reduces blur)
 
# ─────────────────────────────────────────────
# DERIVED TIMING CONSTANTS
# Pre-calculated so state_machine.py doesn't do math inline.
# All based on ROVER_CRUISE_FPS = 0.41 ft/s.
# ─────────────────────────────────────────────
 
# Time to drive between capture points
# state_machine.py uses this to know how long to drive before next stop
# Formula: CAPTURE_EVERY_FT / ROVER_CRUISE_FPS = 2.0 / 0.41 = ~4.9 seconds
DRIVE_BETWEEN_CAPTURES_SEC = CAPTURE_EVERY_FT / ROVER_CRUISE_FPS

# Time to drive one full row
# Formula: ROW_LENGTH_FT / ROVER_CRUISE_FPS = 75.0 / 0.41 = ~183 seconds
DRIVE_ROW_SEC = ROW_LENGTH_FT / ROVER_CRUISE_FPS

# Time to drive between rows (row spacing)
# Formula: ROW_SPACING_FT / ROVER_CRUISE_FPS = 3.0 / 0.41 = ~7.3 seconds
DRIVE_ROW_SPACING_SEC = ROW_SPACING_FT / ROVER_CRUISE_FPS

# Time to pivot 90 degrees in place
# TUNE THIS — run motors.pivot_left() and time how long a 90 degree turn takes
# on your actual surface (soil/tanbark). Adjust until turns are accurate.
PIVOT_90_SEC         = 2.5     # seconds — NEEDS TUNING on real surface
 
# Max seconds to wait for Gemini image analysis to complete
# If analysis takes longer than this, rover moves on anyway
# Based on: drive time between plants (~4.9s) gives Gemini time to process
GEMINI_TIMEOUT_SEC   = 10.0    # seconds before giving up on Gemini response

# ─────────────────────────────────────────────
# WHEEL GEOMETRY
# Used for time-based distance estimation (no encoders).
# At CRUISE_PWM the rover covers ~25 ft/min → ~0.41 ft/sec.
# ─────────────────────────────────────────────
WHEEL_DIAMETER_IN = 7.0        # inches  (7" wheels confirmed in motor spec)
WHEEL_DIAMETER_FT = 0.583      # feet    (7 / 12)
WHEEL_CIRCUMFERENCE_FT = 1.833 # feet    (π × 0.583)

# ─────────────────────────────────────────────
# BACKEND — FastAPI on Oracle Cloud
# Fill in BACKEND_URL and MQTT_BROKER_URL once deployed.
# ─────────────────────────────────────────────
BACKEND_URL     = ""           # e.g. "https://your-oracle-ip/api"
MQTT_BROKER_URL = ""           # e.g. "your-oracle-ip"
MQTT_PORT       = 1883         # standard unencrypted MQTT port
                               # use 8883 if TLS is enabled on the broker
MQTT_KEEPALIVE  = 60           # seconds between MQTT heartbeat pings

# MQTT topics — {session_id} is replaced at runtime by backend_client.py
MQTT_CMD_TOPIC        = "rover/{session_id}/cmd"        # backend → rover  (start / stop commands)
MQTT_STATUS_TOPIC     = "rover/{session_id}/status"     # rover  → backend (running / stopped)
MQTT_TELEMETRY_TOPIC  = "rover/{session_id}/telemetry"  # rover  → backend (battery, gps, heading, timestamp)
MQTT_SCAN_TOPIC       = "scans/new"                     # rover  → backend (new scan result)

# How often the rover publishes a telemetry update while running
TELEMETRY_INTERVAL_SEC = 2.0   # seconds between telemetry publishes

# ─────────────────────────────────────────────
# BACKEND API ENDPOINTS
# Rover calls these directly (HTTP POST) for image analysis.
# Base URL comes from BACKEND_URL above.
# ─────────────────────────────────────────────
ENDPOINT_ANALYZE  = "/images/analyze"   # POST — sends image + GPS coords + session metadata
                                        #        returns: is_diseased, severity, cause, etc.

# ─────────────────────────────────────────────
# FAN
# Cooling fan is powered directly from 5V — always on when Pi is powered.
# No GPIO control needed.
#   Fan (+) → 5VE
#   Fan (−) → GND
# ─────────────────────────────────────────────