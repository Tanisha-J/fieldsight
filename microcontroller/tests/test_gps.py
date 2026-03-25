import serial
import pynmea2

port = "/dev/ttyUSB0" # change when you know what serial port it is
baud = 9600

# pyserial opens the serial port and prepares to read data
ser = serial.Serial(port, baud, timeout=1)

while True:
    line = ser.readline().decode("ascii", errors="ignore") # pyserial reads one line from the GPS

    if line.startswith("$GPGGA"):
        try:
            msg = pynmea2.parse(line)

            print("Lat:", msg.latitude)
            print("Lon:", msg.longitude)

        except pynmea2.ParseError:
            continue