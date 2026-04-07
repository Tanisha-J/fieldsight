import serial
import pynmea2

class GPS:
    # store connection settings
    def __init__(self, port="/dev/ttyUSB0", baud=9600):
        self.port = port
        self.baud = baud
        self.ser = None  # holds serial connection

    # open connection to GPS using pyserial
    def setup(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=1)
        print("GPS connected")

    # read one line from GPS and convert from bytes -> string
    def read_line(self):
        return self.ser.readline().decode("ascii", errors="ignore")

    # turn raw GPS line into usable data
    def parse(self, line):

        # skip empty lines
        if not line:
            return None

        # only use GPGGA lines from NMEA (just gives lat/long)
        if not line.startswith("$GPGGA"):
            return None

        try:
            # pynmea2 to parse GPS sentence
            msg = pynmea2.parse(line)

            # return coordinates in a simple dictionary
            return {
                "lat": msg.latitude,
                "lng": msg.longitude,
                "valid": True
            }

        # skip lines that can't parse
        except pynmea2.ParseError:
            return None

    # keep reading until we get a valid GPS location
    def get_location(self):
        while True:
            line = self.read_line()
            data = self.parse(line)

            # if valid data found, return coordinates
            if data and data["valid"]:
                return {
                    "lat": data["lat"],
                    "lng": data["lng"]
                }


# test the GPS module by itself
if __name__ == "__main__":
    gps = GPS()
    gps.setup()

    while True:
        location = gps.get_location()
        print("Current location:", location)