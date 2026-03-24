"""
config.py - FieldSight Central Configuration

This is the ONLY place where settings and pin numbers live.
Every other file should be importting from here instead of hardcoding values.

    If a pin number needs to change, change it HERE once.

Other files use this:
    from config import MOTOR_LEFT_IN1, ROVER_SPEED, BACKEND_URL
"""

# GPIO PINS — LEFT MOTOR DRIVER (L298N U4)
    # Controls Motor 1 and Motor 2 (left side of rover)

MOTOR_LEFT_IN1 = 17      # GPIO17 → IN1
MOTOR_LEFT_IN2 = 27      # GPIO27 → IN2
MOTOR_LEFT_IN3 = 22      # GPIO22 → IN3
MOTOR_LEFT_IN4 = 23      # GPIO23 → IN4
MOTOR_LEFT_ENA = 18      # GPIO18 (PWM0) → ENA  — controls speed via PWM
MOTOR_LEFT_ENB = 13      # GPIO13 (PWM1) → ENB  — controls speed via PWM


# GPIO PINS — RIGHT MOTOR DRIVER (L298N U1)
    # Controls Motor 3 and Motor 4 (right side of rover)

MOTOR_RIGHT_IN1 = 5      # GPIO5  → IN1
MOTOR_RIGHT_IN2 = 6      # GPIO6  → IN2
MOTOR_RIGHT_IN3 = 16     # GPIO16 → IN3
MOTOR_RIGHT_IN4 = 20     # GPIO20 → IN4
MOTOR_RIGHT_ENA = 12     # GPIO12 (PWM0) → ENA  — controls speed via PWM
MOTOR_RIGHT_ENB = 19     # GPIO19 (PWM1) → ENB  — controls speed via PWM


# GPIO PINS — ENCODERS

# Each motor has two encoder channels (A and B).
# Yellow wire (A channel) and White wire (B channel).
# Blue → 3V3, Green → GND (power wiring, not GPIO)

ENCODER_MOTOR1_A = 4     # Motor 1 A → GPIO4
ENCODER_MOTOR1_B = 7     # Motor 1 B → GPIO7
ENCODER_MOTOR2_A = 8     # Motor 2 A → GPIO8
ENCODER_MOTOR2_B = 9     # Motor 2 B → GPIO9
ENCODER_MOTOR3_A = 10    # Motor 3 A → GPIO10
ENCODER_MOTOR3_B = 11    # Motor 3 B → GPIO11
ENCODER_MOTOR4_A = 24    # Motor 4 A → GPIO24
ENCODER_MOTOR4_B = 25    # Motor 4 B → GPIO25


# GPIO PINS — IMU (MPU6050)
# Connects via I2C (SDA = data, SCL = clock)

IMU_SDA         = 2      # MPU SDA → GPIO2
IMU_SCL         = 3      # MPU SCL → GPIO3
IMU_VDD         = "3V3"  # MPU VDD → 3V3  
IMU_I2C_ADDRESS = 0x68   # MPU6050 default I2C address 


# FAN
# Cooling fan for Raspberry Pi — powered directly - always on when pi is powered
    # Fan + → 5VE
    # Fan - → GND


# CAMERA 
# Both cameras connect via USB directly into the Pi 
# *** Run `ls /dev/video*` on the Pi with both cameras plugged in to confirm indexes.

CAMERA_LEFT_INDEX   = 0      # USB device index for left camera
CAMERA_RIGHT_INDEX  = 2      # USB device index for right camera


CAMERA_WIDTH        = 1280   # pixels — 720p width  
CAMERA_HEIGHT       = 720    # pixels — 720p height 
CAMERA_FPS          = 30     # frames per second    
CAMERA_JPEG_QUALITY = 85     # compression quality  
CAMERA_SAVE_DIR     = "captured_images"  # local folder to save images on pi before upload to cloud

# GPS 
# VK-162 USB GPS connects via USB directly into the Pi 
# *** Run `ls /dev/ttyUSB*` on the Pi with GPS plugged in to confirm serial port.

GPS_PORT      = "/dev/ttyUSB0"  # serial port 
GPS_BAUDRATE  = 9600            # standard baud rate for VK-162
GPS_TIMEOUT   = 1               # seconds to wait for a GPS reading before shutting off and restarting


# ROVER BEHAVIOR 

ROVER_SPEED_MPH    = 1.0    # target speed               
ROVER_SPEED_FPS    = 1.467  # 1 mph × 1.467
CAPTURE_EVERY_FT   = 2.0    # photo trigger distance      
ROW_LENGTH_FT      = 75.0   # length of each crop row     
NUM_ROWS           = 2      # number of rows to survey    
ROW_SPACING_FT     = 3.0    # space between rows          
TURN_ANGLE_DEGREES = 90     # degrees to turn between rows

# Small pause after stopping before capturing so image is not blurry
SCAN_SETTLE_TIME_SEC = 0.3


# ENCODER / DISTANCE TRACKING
# Used to convert encoder pulses into real distance traveled in feet.

WHEEL_DIAMETER_IN = 8.0          # inches   
WHEEL_DIAMETER_FT = 8.0 / 12.0  # feet     (converted for distance math)
ENCODER_PPR       = 341.2        # pulses per revolution — confirm with motor team
# Cytron 12V 37mm at 30:1 gear ratio is typically ~341 PPR????


# BACKEND 
# FastAPI backend runs on Oracle Cloud????
# MQTT handles real time start/stop commands from the farmer dashboard.

BACKEND_URL     = ""  # fill in when backend ready
MQTT_BROKER_URL = ""          # fill in when backend ready
### MQTT_PORT       = ?????
### MQTT_KEEPALIVE  = 60    # seconds between MQTT heartbeat pings ????

# MQTT topic format — session_id gets filled in at runtime by backend_client.py
MQTT_CMD_TOPIC    = "rover/{session_id}/cmd"     # backend → rover (start/stop)
MQTT_STATUS_TOPIC = "rover/{session_id}/status"  # rover → backend (running/stopped)
MQTT_SCAN_TOPIC   = "scans/new"                  # rover → backend (new scan data)

