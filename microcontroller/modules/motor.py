"""
motor.py - FieldSight Motor Control Module

This file controls the physical wheels of the rover.
It talks to two L298N motor drivers which then power the four motors.

Left driver  (L298N U4) → controls Motor 1 and Motor 2 (left wheels)
Right driver (L298N U1) → controls Motor 3 and Motor 4 (right wheels)

How other files use this:
    from modules.motor import Motor

    motor = Motor()
    motor.setup()
    motor.forward()
    motor.stop()
    motor.cleanup()
"""

# RPi.GPIO is the library that lets Python talk to the Pi's physical pins
    # what actually sends electricity through the GPIO pins
import RPi.GPIO as GPIO

# time lets us pause the code for a set number of seconds
# *** used for things like waiting during a turn - unsure if this is needed????
import time

# logging prints messages to the terminal so you can see what's happening
import logging

# import all our pin numbers from config.py - CHANGE ON CONFIG.PY ONLY
from config import (
    MOTOR_LEFT_IN1,   # direction pin - left motors
    MOTOR_LEFT_IN2,   # direction pin - left motors
    MOTOR_LEFT_IN3,   # direction pin - left motors
    MOTOR_LEFT_IN4,   # direction pin - left motors
    MOTOR_LEFT_ENA,   # speed pin - left motors (PWM)
    MOTOR_LEFT_ENB,   # speed pin - left motors (PWM)
    MOTOR_RIGHT_IN1,  # direction pin - right motors
    MOTOR_RIGHT_IN2,  # direction pin - right motors
    MOTOR_RIGHT_IN3,  # direction pin - right motors
    MOTOR_RIGHT_IN4,  # direction pin - right motors
    MOTOR_RIGHT_ENA,  # speed pin - right motors (PWM)
    MOTOR_RIGHT_ENB,  # speed pin - right motors (PWM)
    ROVER_SPEED_MPH,  # target speed from proposal (1 mph)
    TURN_ANGLE_DEGREES # how many degrees to turn (90)
)

# sets up logging so messages print to terminal
logger = logging.getLogger(__name__)

#***DOUBLE CHECK THIS
# PWM_FREQUENCY is how fast the PWM signal flickers per second
# 1000 Hz means it flickers 1000 times per second 
PWM_FREQUENCY = 1000

# DEFAULT_SPEED is the duty cycle percentage for normal driving
# Duty cycle means what percentage of the time the pin is ON
# 75 means the pin is ON 75% of the time = 75% power = 75% speed
# Range is 0 (stopped) to 100 (full speed)
DEFAULT_SPEED = 75

# TURN_SPEED is slower than driving speed
# Slower turns are more accurate and easier to control
TURN_SPEED = 50

# TURN_DURATION is how many seconds the rover turns for
# This is a placeholder - real version uses IMU to measure exact angle
# Will need to be tuned during hardware testing
TURN_DURATION = 1.0



class Motor:
    """
    Controls all four wheels of the FieldSight rover.

    explanation for how state_machine.py uses this:
        motor = Motor()
        motor.setup()       # always call this first
        motor.forward()     # start driving
        motor.stop()        # stop wheels
        motor.turn_right_90()  # turn between rows
        motor.cleanup()     # always call this last
    """
    """
    class Motor:              # example

    def __init__(self):   # runs automatically when you create the object
        self.pwm_left_a = None   # this object has a pwm_left_a, starts empty

    def setup(self):      # functions this object can do
    def forward(self):    
    def stop(self):      
    """

    def __init__(self):
        """
        __init__ runs once when you create the Motor object.
        It just sets up variables - nothing actually happens to the
        hardware yet. setup() is what actually activates the pins.
        """

        # These will hold our PWM objects once setup() runs
        # PWM objects are what control the speed of each motor
        # They start as None because they don't exist yet
        self.pwm_left_a  = None   # controls speed of Motor 1
        self.pwm_left_b  = None   # controls speed of Motor 2
        self.pwm_right_a = None   # controls speed of Motor 3
        self.pwm_right_b = None   # controls speed of Motor 4

        # is_setup tracks whether setup() has been called
        # used to prevent running motors before pins are ready
        self.is_setup = False

        logger.info("Motor object created. Call setup() before use.")


    def setup(self):
        """
        Activates all the GPIO pins and gets them ready to use, turning on motor system
        """

        # GPIO.setmode tells the Pi which numbering system to use
        # GPIO.BCM means we use the GPIO numbers (like GPIO17)
        GPIO.setmode(GPIO.BCM)

        # GPIO.setup tells the Pi whether each pin is sending or receiving
        # GPIO.OUT means this pin sends signals OUT to the motor driver

        # left driver direction pins
        GPIO.setup(MOTOR_LEFT_IN1, GPIO.OUT)
        GPIO.setup(MOTOR_LEFT_IN2, GPIO.OUT)
        GPIO.setup(MOTOR_LEFT_IN3, GPIO.OUT)
        GPIO.setup(MOTOR_LEFT_IN4, GPIO.OUT)

        # left driver speed pins
        GPIO.setup(MOTOR_LEFT_ENA, GPIO.OUT)
        GPIO.setup(MOTOR_LEFT_ENB, GPIO.OUT)

        # right driver direction pins
        GPIO.setup(MOTOR_RIGHT_IN1, GPIO.OUT)
        GPIO.setup(MOTOR_RIGHT_IN2, GPIO.OUT)
        GPIO.setup(MOTOR_RIGHT_IN3, GPIO.OUT)
        GPIO.setup(MOTOR_RIGHT_IN4, GPIO.OUT)

        # right driver speed pins
        GPIO.setup(MOTOR_RIGHT_ENA, GPIO.OUT)
        GPIO.setup(MOTOR_RIGHT_ENB, GPIO.OUT)

        # GPIO.PWM creates a PWM object on a pin at a set frequency
        # First argument is the pin number
        # Second argument is the frequency in Hz (how fast it flickers)
        self.pwm_left_a  = GPIO.PWM(MOTOR_LEFT_ENA,  PWM_FREQUENCY)
        self.pwm_left_b  = GPIO.PWM(MOTOR_LEFT_ENB,  PWM_FREQUENCY)
        self.pwm_right_a = GPIO.PWM(MOTOR_RIGHT_ENA, PWM_FREQUENCY)
        self.pwm_right_b = GPIO.PWM(MOTOR_RIGHT_ENB, PWM_FREQUENCY)

        # .start() activates the PWM signal at a given duty cycle
        # starting at 0 means 0% power which means motors not moving yet
        # Speed gets set later when forward() or other functions are called
        self.pwm_left_a.start(0)
        self.pwm_left_b.start(0)
        self.pwm_right_a.start(0)
        self.pwm_right_b.start(0)

        # mark setup as done so other functions know they can run
        self.is_setup = True

        logger.info("Setup complete. All pins ready.")


    def forward(self, speed=DEFAULT_SPEED):
        """
        Drives the rover straight forward.

        speed is a number from 0 to 100 representing power percentage
        Default is DEFAULT_SPEED (75%) which comes from the constant above

        How forward direction works on L298N:
            IN1=HIGH, IN2=LOW → motor spins forward
            IN3=HIGH, IN4=LOW → motor spins forward
        """

        # safety check - don't run if setup() was never called
        if not self.is_setup:
            logger.error("[Motor] Cannot drive - setup() has not been called")
            return

        # GPIO.HIGH means turn the pin ON (send electricity through it)
        # GPIO.LOW means turn the pin OFF

        # set left motors to spin forward
        # IN1 HIGH + IN2 LOW = forward direction for Motor 1
        GPIO.output(MOTOR_LEFT_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_LEFT_IN2, GPIO.LOW)
        # IN3 HIGH + IN4 LOW = forward direction for Motor 2
        GPIO.output(MOTOR_LEFT_IN3, GPIO.HIGH)
        GPIO.output(MOTOR_LEFT_IN4, GPIO.LOW)

        # set right motors to spin forward
        # same pattern - IN1 HIGH + IN2 LOW = forward
        GPIO.output(MOTOR_RIGHT_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_RIGHT_IN2, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN3, GPIO.HIGH)
        GPIO.output(MOTOR_RIGHT_IN4, GPIO.LOW)

        # .ChangeDutyCycle sets the speed
        # speed=75 means 75% power
        # all four channels get the same speed for straight driving
        self.pwm_left_a.ChangeDutyCycle(speed)
        self.pwm_left_b.ChangeDutyCycle(speed)
        self.pwm_right_a.ChangeDutyCycle(speed)
        self.pwm_right_b.ChangeDutyCycle(speed)

        logger.info(f"[Motor] Driving forward at {speed}% speed")


    def stop(self):
        """
        Stops all four wheels immediately.

        Sets all direction pins LOW and speed to 0.
        This is a hard stop - wheels stop spinning right away.
        """

        if not self.is_setup:
            logger.error("[Motor] Cannot stop - setup() has not been called")
            return

        # set all direction pins LOW
        # when both IN pins are LOW the motor driver cuts power to the motor
        GPIO.output(MOTOR_LEFT_IN1,  GPIO.LOW)
        GPIO.output(MOTOR_LEFT_IN2,  GPIO.LOW)
        GPIO.output(MOTOR_LEFT_IN3,  GPIO.LOW)
        GPIO.output(MOTOR_LEFT_IN4,  GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN1, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN2, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN3, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN4, GPIO.LOW)

        # set speed to 0 on all PWM channels
        self.pwm_left_a.ChangeDutyCycle(0)
        self.pwm_left_b.ChangeDutyCycle(0)
        self.pwm_right_a.ChangeDutyCycle(0)
        self.pwm_right_b.ChangeDutyCycle(0)

        logger.info("[Motor] Stopped")


    def turn_right_90(self, speed=TURN_SPEED):
        """
        Turns the rover 90 degrees to the right.
        Used between crop rows.

        Tank drive turning works by spinning the two sides in
        opposite directions at the same time.
        Left wheels go forward, right wheels go backward = turn right.

        NOTE: TURN_DURATION is a placeholder time value.
        Real version should use IMU to measure the actual angle.
        Motor team needs to tune TURN_DURATION during hardware testing.
        """

        if not self.is_setup:
            logger.error("[Motor] Cannot turn - setup() has not been called")
            return

        logger.info("[Motor] Turning right 90 degrees...")

        # left wheels forward
        # IN1 HIGH + IN2 LOW = forward
        GPIO.output(MOTOR_LEFT_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_LEFT_IN2, GPIO.LOW)
        GPIO.output(MOTOR_LEFT_IN3, GPIO.HIGH)
        GPIO.output(MOTOR_LEFT_IN4, GPIO.LOW)

        # right wheels backward
        # IN1 LOW + IN2 HIGH = backward (opposite of forward)
        GPIO.output(MOTOR_RIGHT_IN1, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_RIGHT_IN3, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN4, GPIO.HIGH)

        # set speed for the turn
        self.pwm_left_a.ChangeDutyCycle(speed)
        self.pwm_left_b.ChangeDutyCycle(speed)
        self.pwm_right_a.ChangeDutyCycle(speed)
        self.pwm_right_b.ChangeDutyCycle(speed)

        # wait for the turn to complete
        # time.sleep pauses the code for TURN_DURATION seconds
        # during this time the wheels keep spinning
        time.sleep(TURN_DURATION)

        # stop after the turn is done
        self.stop()

        logger.info("[Motor] Turn complete")


    def turn_left_90(self, speed=TURN_SPEED):
        """
        Turns the rover 90 degrees to the left.
        Mirror image of turn_right_90.

        Right wheels go forward, left wheels go backward = turn left.
        """

        if not self.is_setup:
            logger.error("[Motor] Cannot turn - setup() has not been called")
            return

        logger.info("[Motor] Turning left 90 degrees...")

        # left wheels backward
        GPIO.output(MOTOR_LEFT_IN1, GPIO.LOW)
        GPIO.output(MOTOR_LEFT_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_LEFT_IN3, GPIO.LOW)
        GPIO.output(MOTOR_LEFT_IN4, GPIO.HIGH)

        # right wheels forward
        GPIO.output(MOTOR_RIGHT_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_RIGHT_IN2, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_IN3, GPIO.HIGH)
        GPIO.output(MOTOR_RIGHT_IN4, GPIO.LOW)

        # set speed
        self.pwm_left_a.ChangeDutyCycle(speed)
        self.pwm_left_b.ChangeDutyCycle(speed)
        self.pwm_right_a.ChangeDutyCycle(speed)
        self.pwm_right_b.ChangeDutyCycle(speed)

        # wait for turn to complete then stop
        time.sleep(TURN_DURATION)
        self.stop()

        logger.info("[Motor] Turn complete")


    def cleanup(self):
        """
        Shuts everything down safely.
        ALWAYS call this when you are done using the motors.

        If you don't call this the GPIO pins stay active even after
        your code stops running which can damage the Pi or motors.
        Think of it like properly shutting down a computer instead
        of just pulling the power cable.
        """

        if not self.is_setup:
            return

        # stop all motors first
        self.stop()

        # .stop() on a PWM object turns off the PWM signal completely
        # different from the stop() method above which just sets speed to 0
        self.pwm_left_a.stop()
        self.pwm_left_b.stop()
        self.pwm_right_a.stop()
        self.pwm_right_b.stop()

        # GPIO.cleanup() resets ALL pins back to their default state
        # this is the safe shutdown for the entire GPIO system
        GPIO.cleanup()

        self.is_setup = False

        logger.info("[Motor] Cleanup complete. GPIO pins released.")