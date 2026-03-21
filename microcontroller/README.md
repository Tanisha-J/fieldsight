# Microcontroller

This folder contains all Raspberry Pi control logic.

## Structure

- modules/ → controls hardware components (motor, GPS, camera)
- tests/ → used to test each module individually
- docs/ → contains documentation

## Components

### Motor Module
Handles rover movement: forward, backward, stop, start, turn

### GPS Module
Retrieves location coordinates of the rover

### Camera Module
Captures images of crops for backend analysis

## Goal

To control rover movement, collect crop and gps data, and send data to the backend system.