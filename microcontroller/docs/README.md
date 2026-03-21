# Microcontroller Documentation

## Modules

### motor.py
Controls rover movement.
Functions:
    - move_forward()
    - move_backward()
    - stop()

### gps.py
Retrieves GPS coordinates of the rover.

### camera.py
Captures images of crops for disease detection.

## Data Flow

1. Camera captures image
2. GPS provides location
3. Data is processed by Raspberry Pi
4. Data is sent to backend
5. Backend stores data and updates UI


## Status

Skeletal functions need to be created. I've done some research and these are some of the functions you should be using. 

## Skeletal Examples 

### Motor skeleton
 def move_forward()
 def move_backward()
 def turn_left()
 def stop()

### GPS skeleton
 def get_coordinates()
 def __init__()
 def is_connected()

### Camera skeleton
 def __init__()
 def take_picture()
 def get_last_image()


