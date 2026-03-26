import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

led = 23
GPIO.setup(led, GPIO.OUT)

print("LED on")
GPIO.output(led, 1)
time.sleep(1)
print("LED off")
GPIO.output(led, 0)

GPIO.cleanup()   
