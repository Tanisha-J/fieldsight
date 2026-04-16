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

## Pi login credentials
username: fieldsight
password: 1234
hostname: fieldsightpi.local

## Connect to Pi 
be on the same network, go to terminal
```bash
ssh fieldsight@fieldsightpi.local
ssh fieldsight@192.168.1.204
```
## Connect to Hotspot
hotspot name: neha
1. Turn phone hotspot on
2. Power on Pi, wait for boot
3. Connect to hotspot on laptop
4. SSH in

switch pi from wifi to hotspot
```bash
sudo nmcli connection up wifi
```

## Terminal Setup
go to project root
```bash
cd ~/fieldsight/microcontroller
```
pull code onto pi
```bash
git checkout "branchname"
git pull
```
## Install Python dependencies
```bash
pip install -r requirements.txt --break-system-packages
```
## Running the rover
```bash
python3 main.py
```
wait for this command to start
"Subscribed to rover/cmd"

## Hardware Tests
motor test
```bash
python3 -c "
import sys, time
sys.path.insert(0, '.')
from modules.motor import MotorController
motors = MotorController()
motors.forward()
time.sleep(3)
motors.stop()
motors.cleanup()
"
```
camera test
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from modules.camera import CameraController
camera = CameraController()
left, right = camera.capture_both()
print(f'Left cam: {left}')
print(f'Right cam: {right}')
"
```
gps test
```bash
python3 -c "
import sys, time
sys.path.insert(0, '.')
from modules.gps import GPS
gps = GPS()
gps.open()
time.sleep(3)
print(gps.get_location())
gps.close()
"
```
image upload to backend servers test
```bash
python3 -c "
import sys, glob
sys.path.insert(0, '.')
from modules.backend_client import BackendClient
client = BackendClient(farmer_id=8, rover_id=1)
images = glob.glob('captured_images/left_*.jpg')
r = client.upload_scan(images[0], 1, 37.39, -121.85)
print(r.status_code, r.text)
"
```


