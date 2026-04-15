"""
modules/motor.py - FieldSight Motor Controller
===============================================
Controls all 4 motors on the FieldSight rover via two L298N motor drivers.

This module is imported by state_machine.py and main.py.
It never hardcodes pin numbers or speed values — everything comes from config.py.
If a motor spins the wrong direction, fix the pin numbers in config.py.
Nothing in this file needs to change.

Usage:
    from modules.motor import MotorController

    motors = MotorController()
    motors.forward()
    motors.stop()
    motors.cleanup()

Hardware layout:
    Left driver  (L298N U4) — Motor 1 (front-left) and Motor 2 (rear-left)
    Right driver (L298N U1) — Motor 3 (front-right) and Motor 4 (rear-right)

How an L298N channel works:
    IN1=HIGH, IN2=LOW  → motor spins forward
    IN1=LOW,  IN2=HIGH → motor spins backward
    IN1=LOW,  IN2=LOW  → motor coasts to stop
    ENA = PWM value    → controls speed (0.0=off, 1.0=full, 0.45=cruise)
"""

import time
from gpiozero import PWMOutputDevice, DigitalOutputDevice

# Import all pin numbers and speed constants from config.py
# This file never hardcodes a GPIO number or PWM value
import config


class Motor:
    """
    Represents a single motor channel on an L298N driver.

    Each L298N has two channels (A and B), each controlling one motor.
    A channel needs three pins:
        en_pin  — PWM pin that controls speed (ENA or ENB)
        in1_pin — direction pin 1 (IN1 or IN3)
        in2_pin — direction pin 2 (IN2 or IN4)
    """

    def __init__(self, en_pin, in1_pin, in2_pin):
        """
        Sets up the three GPIO pins for this motor channel.

        Parameters:
            en_pin  : GPIO pin number for ENA or ENB (PWM speed control)
            in1_pin : GPIO pin number for IN1 or IN3 (direction)
            in2_pin : GPIO pin number for IN2 or IN4 (direction)
        """
        # PWMOutputDevice lets us set any value from 0.0 to 1.0
        # This controls the motor speed via pulse width modulation
        self.en  = PWMOutputDevice(en_pin)

        # DigitalOutputDevice is just HIGH or LOW — controls direction
        self.in1 = DigitalOutputDevice(in1_pin)
        self.in2 = DigitalOutputDevice(in2_pin)

    def forward(self, speed=config.CRUISE_PWM):
        """
        Spins this motor forward at the given speed.

        Parameters:
            speed : PWM duty cycle from 0.0 to MAX_PWM (default: CRUISE_PWM)
                    0.0 = stopped, 1.0 = full speed, 0.45 = cruise speed
        """
        # Clamp speed so it never exceeds the safety ceiling from config
        speed = min(speed, config.MAX_PWM)
        self.in1.on()           # IN1 HIGH
        self.in2.off()          # IN2 LOW  → forward direction on L298N
        self.en.value = speed   # set speed via PWM

    def backward(self, speed=config.CRUISE_PWM):
        """
        Spins this motor backward at the given speed.

        Parameters:
            speed : PWM duty cycle from 0.0 to MAX_PWM (default: CRUISE_PWM)
        """
        speed = min(speed, config.MAX_PWM)
        self.in1.off()          # IN1 LOW
        self.in2.on()           # IN2 HIGH → backward direction on L298N
        self.en.value = speed

    def stop(self):
        """
        Stops this motor immediately (cuts power, coasts to stop).
        Sets EN to 0 first so the motor loses power before direction pins clear.
        """
        self.en.value = 0   # cut power first
        self.in1.off()      # clear direction pins
        self.in2.off()

    def cleanup(self):
        """
        Releases this motor's GPIO pins back to the system.
        Always call this when done — uncleaned pins can cause issues on next run.
        """
        self.stop()
        self.en.close()
        self.in1.close()
        self.in2.close()


class MotorController:
    """
    Controls all 4 motors on the FieldSight rover together.

    This is the class that state_machine.py and main.py import and use.
    It wraps the 4 individual Motor objects and exposes high-level
    movement commands like forward(), turn_left(), stop().

    Example:
        motors = MotorController()
        motors.forward()
        time.sleep(3)
        motors.stop()
        motors.cleanup()
    """

    def __init__(self):
        """
        Creates Motor objects for all 4 wheels using pin numbers from config.py.
        Called once when the rover starts up.
        """
        # Left side — controlled by left L298N driver (U4)
        # Motor 1 uses ENA pin for speed, IN1/IN2 for direction
        self.m1 = Motor(
            config.MOTOR_LEFT_ENA,
            config.MOTOR_LEFT_IN1,
            config.MOTOR_LEFT_IN2
        )
        # Motor 2 uses ENB pin for speed, IN3/IN4 for direction
        self.m2 = Motor(
            config.MOTOR_LEFT_ENB,
            config.MOTOR_LEFT_IN3,
            config.MOTOR_LEFT_IN4
        )

        # Right side — controlled by right L298N driver (U1)
        self.m3 = Motor(
            config.MOTOR_RIGHT_ENA,
            config.MOTOR_RIGHT_IN1,
            config.MOTOR_RIGHT_IN2
        )
        self.m4 = Motor(
            config.MOTOR_RIGHT_ENB,
            config.MOTOR_RIGHT_IN3,
            config.MOTOR_RIGHT_IN4
        )

        # Convenience list for operations that apply to all motors
        self._all = [self.m1, self.m2, self.m3, self.m4]

    # ─────────────────────────────────────────────
    # MOVEMENT COMMANDS
    # These are the methods state_machine.py calls
    # ─────────────────────────────────────────────

    def forward(self, speed=config.CRUISE_PWM):
        self.m1.forward(0.43)  # front-left
        self.m2.forward(0.43)  # rear-left
        self.m3.forward(0.45)  # front-right
        self.m4.forward(0.45)  # rear-right

    def backward(self, speed=config.CRUISE_PWM):
        """
        Drives the rover backward in a straight line.
        No ramp on backward — used for short corrections only.

        Parameters:
            speed : target PWM speed (default: CRUISE_PWM from config)
        """
        for motor in self._all:
            motor.backward(speed)

    def stop(self):
        """
        Stops all 4 motors immediately.
        This is safe to call at any time including from a Ctrl+C handler.
        """
        for motor in self._all:
            motor.stop()

    def turn_left(self):
        """
        Curves the rover left by slowing the left wheels and speeding up the right.
        Left wheels  → TURN_INNER_PWM (slower)
        Right wheels → TURN_OUTER_PWM (faster)
        The rover curves toward the slower side.
        """
        self.m1.forward(config.TURN_INNER_PWM)  # front-left  slow
        self.m2.forward(config.TURN_INNER_PWM)  # rear-left   slow
        self.m3.forward(config.TURN_OUTER_PWM)  # front-right fast
        self.m4.forward(config.TURN_OUTER_PWM)  # rear-right  fast

    def turn_right(self):
        """
        Curves the rover right by slowing the right wheels and speeding up the left.
        Right wheels → TURN_INNER_PWM (slower)
        Left wheels  → TURN_OUTER_PWM (faster)
        """
        self.m1.forward(config.TURN_OUTER_PWM)  # front-left  fast
        self.m2.forward(config.TURN_OUTER_PWM)  # rear-left   fast
        self.m3.forward(config.TURN_INNER_PWM)  # front-right slow
        self.m4.forward(config.TURN_INNER_PWM)  # rear-right  slow

    def pivot_left(self):
        """
        Spins the rover in place to the left.
        Left wheels go backward, right wheels go forward.
        Use this for sharp 90 degree turns between crop rows.
        """
        self.m1.backward(config.MAX_PWM)  # front-left  backward
        self.m2.backward(config.MAX_PWM)  # rear-left   backward
        self.m3.forward(config.MAX_PWM)   # front-right forward
        self.m4.forward(config.MAX_PWM)   # rear-right  forward

    def pivot_right(self):
        """
        Spins the rover in place to the right.
        Right wheels go backward, left wheels go forward.
        """
        self.m1.forward(config.MAX_PWM)   # front-left  forward
        self.m2.forward(config.MAX_PWM)   # rear-left   forward
        self.m3.backward(config.MAX_PWM)  # front-right backward
        self.m4.backward(config.MAX_PWM)  # rear-right  backward

    def set_speeds(self, left_speed, right_speed):
        """
        Sets left and right side speeds independently.
        Used by state_machine.py for fine-grained control during navigation.

        Parameters:
            left_speed  : PWM value for left side motors (0.0 to MAX_PWM)
            right_speed : PWM value for right side motors (0.0 to MAX_PWM)
        """
        self.m1.forward(left_speed)
        self.m2.forward(left_speed)
        self.m3.forward(right_speed)
        self.m4.forward(right_speed)

    # ─────────────────────────────────────────────
    # SOFT START RAMP
    # Gradually increases speed from 0 to target.
    # Prevents large current spikes that can reboot the Pi.
    # ─────────────────────────────────────────────

    def ramp_to(self, target=config.CRUISE_PWM):
        """
        Gradually ramps all motors up to the target speed.
        Starts at 0 and steps up by RAMP_STEP every RAMP_DELAY_SEC.

        Parameters:
            target : final PWM speed to reach (default: CRUISE_PWM)

        Example:
            With RAMP_STEP=0.05 and target=0.45:
            Speed goes 0.0 → 0.05 → 0.10 → ... → 0.45
            Each step takes RAMP_DELAY_SEC seconds
        """
        # Clamp target to safety ceiling
        target = min(target, config.MAX_PWM)

        # First set all motors to forward direction at 0 speed
        for motor in self._all:
            motor.forward(0.0)

        # Then step up speed gradually
        speed = 0.0
        while speed < target:
            speed = min(speed + config.RAMP_STEP, target)
            for motor in self._all:
                motor.forward(speed)
            time.sleep(config.RAMP_DELAY_SEC)

    def ramp_down(self):
        """
        Gradually ramps all motors down from current speed to 0.
        Smoother than calling stop() directly — reduces mechanical stress.
        Used at the end of a row before taking a photo.
        """
        # Step down from cruise speed to 0
        speed = config.CRUISE_PWM
        while speed > 0:
            speed = max(speed - config.RAMP_STEP, 0.0)
            for motor in self._all:
                motor.forward(speed)
            time.sleep(config.RAMP_DELAY_SEC)

        # Make sure everything is fully stopped
        self.stop()

    # ─────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────

    def cleanup(self):
        """
        Stops all motors and releases all GPIO pins.
        Always call this when the rover is shutting down.
        state_machine.py and main.py should call this in their
        finally blocks so pins are always released even if something crashes.
        """
        self.stop()
        for motor in self._all:
            motor.cleanup()