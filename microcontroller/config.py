"""
config.py - FieldSight Central Configuration

This is the ONLY place where settings and pin numbers live.
Every other file should be importing from here instead of hardcoding values.
    If a setting needs to change, change it HERE once.

Other files use this:
    from config import MOTOR_LEFT_IN1, CRUISE_PWM, BACKEND_URL
"""

# GPIO PINS — LEFT MOTOR DRIVER (L298N U4)
# Controls Motor 1 (front-left) and Motor 2 (rear-left)

MOTOR_LEFT_IN1 = 17      # GPIO17 → IN1  (Motor 1 direction)
MOTOR_LEFT_IN2 = 27      # GPIO27 → IN2  (Motor 1 direction)
MOTOR_LEFT_IN3 = 23      # GPIO22 → IN3  (Motor 2 direction)
MOTOR_LEFT_IN4 = 22      # GPIO23 → IN4  (Motor 2 direction)
MOTOR_LEFT_ENA = 18      # GPIO18 (PWM0) → ENA  (Motor 1 speed)
MOTOR_LEFT_ENB = 13      # GPIO13 (PWM1) → ENB  (Motor 2 speed)

# GPIO PINS — RIGHT MOTOR DRIVER (L298N U1)
# Controls Motor 3 (front-right) and Motor 4 (rear-right)
MOTOR_RIGHT_IN1 = 5      # GPIO5  → IN1  (Motor 3 direction)
MOTOR_RIGHT_IN2 = 6      # GPIO6  → IN2  (Motor 3 direction)
MOTOR_RIGHT_IN3 = 16     # GPIO16 → IN3  (Motor 4 direction)
MOTOR_RIGHT_IN4 = 20     # GPIO20 → IN4  (Motor 4 direction)
MOTOR_RIGHT_ENA = 12     # GPIO12 (PWM0) → ENA  (Motor 3 speed)
MOTOR_RIGHT_ENB = 19     # GPIO19 (PWM1) → ENB  (Motor 4 speed)


# MOTOR PWM SPEED CONSTANTS
# 0.0 = off, 1.0 = full speed
# Hardware supports 0.0–1.0 but we cap in software at MAX_PWM

# At 45% PWM on 30 RPM motors with 7" wheels:
#   Speed = 0.28 mph
#   Current = 5–6A average draw across all 4 motors
#   150 ft run = 6 minutes
 
CRUISE_PWM      = 0.45   # normal straight-line driving
TURN_INNER_PWM  = 0.30   # inside wheels during a turn
TURN_OUTER_PWM  = 0.60   # outside wheels during a turn
MAX_PWM         = 0.60   # hard upper limit

# instead of jumping to CRUISE_PWM instantly, step up by RAMP_STEP every RAMP_DELAY_SEC to reduce current spikes
RAMP_STEP       = 0.05   # PWM increment per step
RAMP_DELAY_SEC  = 0.10   # seconds between ramp steps


# GPIO PINS — IMU 
# Communicates over I2C 
# Use smbus2: bus = smbus2.SMBus(1), then read registers via bus.read_byte_data()

IMU_SDA         = 2      # GPIO2 → SDA (I2C data)
IMU_SCL         = 3      # GPIO3 → SCL (I2C clock)
IMU_I2C_ADDRESS = 0x68   # MPU6050 default I2C address (AD0 pin LOW)
                         # If AD0 is pulled HIGH, address becomes 0x69


# CAMERA
# Both cameras connect via USB
# run `ls /dev/video*` with both cameras plugged in to confirm.

CAMERA_FRONT_INDEX  = 0      # USB index for front-facing camera
CAMERA_SIDE_INDEX   = 1      # USB index for side-facing camera
                              # (was 2 — recheck with `v4l2-ctl --list-devices`)
CAMERA_WIDTH        = 1280   # capture width in pixels  (720p)
CAMERA_HEIGHT       = 720    # capture height in pixels (720p)
CAMERA_FPS          = 30     # frames per second
CAMERA_JPEG_QUALITY = 85     # JPEG compression quality (0–100)
CAMERA_SAVE_DIR     = "captured_images"  # local folder on Pi before upload


# GPS 
# Run `ls /dev/ttyUSB*` to confirm port 

GPS_PORT        = "/dev/ttyUSB0"   # serial port
GPS_BAUDRATE    = 9600             # VK-162 default baud rate
GPS_TIMEOUT     = 1                # seconds before giving up on a read

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

CAPTURE_EVERY_FT     = 2.0     # take a photo every N feet traveled
ROW_LENGTH_FT        = 75.0    # length of each crop row to survey
NUM_ROWS             = 2       # number of rows in the field
ROW_SPACING_FT       = 3.0     # distance between row centers
TURN_ANGLE_DEGREES   = 90      # heading change between rows

SCAN_SETTLE_TIME_SEC = 0.3     # pause after stopping before capturing (reduces blur)

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