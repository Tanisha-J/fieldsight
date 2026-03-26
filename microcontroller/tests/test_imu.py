#!/usr/bin/env python3
"""
MPU6050 Test Script for Raspberry Pi 4
---------------------------------------
Tests I2C communication, reads accelerometer, gyroscope,
and temperature data from the MPU6050.

Wiring:
  MPU6050 VCC  -> Pi 3.3V (Pin 1)
  MPU6050 GND  -> Pi GND  (Pin 6)
  MPU6050 SDA  -> Pi SDA  (Pin 3, GPIO 2)
  MPU6050 SCL  -> Pi SCL  (Pin 5, GPIO 3)
  MPU6050 AD0  -> GND     (I2C address = 0x68)
               -> 3.3V    (I2C address = 0x69)

Setup:
  sudo apt install python3-smbus i2c-tools
  pip3 install smbus2
  sudo raspi-config  -> Interface Options -> I2C -> Enable
"""

import time
import sys

try:
    import smbus2
except ImportError:
    print("[ERROR] smbus2 not found. Install it with: pip3 install smbus2")
    sys.exit(1)

# ── MPU6050 Register Map ───────────────────────────────────────────────────────
MPU6050_ADDR       = 0x68   # AD0 low; use 0x69 if AD0 is pulled high
PWR_MGMT_1         = 0x6B
SMPLRT_DIV         = 0x19
CONFIG             = 0x1A
GYRO_CONFIG        = 0x1B
ACCEL_CONFIG       = 0x1C
ACCEL_XOUT_H       = 0x3B
TEMP_OUT_H         = 0x41
GYRO_XOUT_H        = 0x43
WHO_AM_I           = 0x75

# ── Scale factors ──────────────────────────────────────────────────────────────
ACCEL_SCALE = 16384.0   # ±2 g  → LSB/g
GYRO_SCALE  = 131.0     # ±250 °/s → LSB/(°/s)

I2C_BUS = 1             # /dev/i2c-1 on Pi 4


def read_word_2c(bus, addr, reg):
    """Read a signed 16-bit big-endian value from two consecutive registers."""
    high = bus.read_byte_data(addr, reg)
    low  = bus.read_byte_data(addr, reg + 1)
    val  = (high << 8) | low
    return val - 65536 if val >= 0x8000 else val


def init_mpu6050(bus):
    """Wake the MPU6050 and apply basic configuration."""
    # Wake up (clear SLEEP bit)
    bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0x00)
    time.sleep(0.1)

    # Sample rate = gyro output / (1 + SMPLRT_DIV)  →  1 kHz / (1+7) = 125 Hz
    bus.write_byte_data(MPU6050_ADDR, SMPLRT_DIV, 0x07)

    # Low-pass filter: bandwidth ~44 Hz
    bus.write_byte_data(MPU6050_ADDR, CONFIG, 0x03)

    # Gyro full-scale: ±250 °/s
    bus.write_byte_data(MPU6050_ADDR, GYRO_CONFIG, 0x00)

    # Accel full-scale: ±2 g
    bus.write_byte_data(MPU6050_ADDR, ACCEL_CONFIG, 0x00)


def read_all(bus):
    """Return a dict with accel (g), gyro (°/s), and temperature (°C)."""
    ax = read_word_2c(bus, MPU6050_ADDR, ACCEL_XOUT_H)     / ACCEL_SCALE
    ay = read_word_2c(bus, MPU6050_ADDR, ACCEL_XOUT_H + 2) / ACCEL_SCALE
    az = read_word_2c(bus, MPU6050_ADDR, ACCEL_XOUT_H + 4) / ACCEL_SCALE

    raw_temp = read_word_2c(bus, MPU6050_ADDR, TEMP_OUT_H)
    temp_c   = raw_temp / 340.0 + 36.53

    gx = read_word_2c(bus, MPU6050_ADDR, GYRO_XOUT_H)     / GYRO_SCALE
    gy = read_word_2c(bus, MPU6050_ADDR, GYRO_XOUT_H + 2) / GYRO_SCALE
    gz = read_word_2c(bus, MPU6050_ADDR, GYRO_XOUT_H + 4) / GYRO_SCALE

    return dict(ax=ax, ay=ay, az=az, gx=gx, gy=gy, gz=gz, temp=temp_c)


def run_self_test(bus):
    """
    Minimal self-test: compares accel Z at rest against expected ~1 g.
    Returns True if the sensor appears healthy.
    """
    samples = [read_all(bus) for _ in range(10)]
    avg_az = sum(s["az"] for s in samples) / len(samples)
    # At rest flat on a desk, Z should be close to ±1 g
    ok = 0.8 <= abs(avg_az) <= 1.2
    print(f"  Self-test — average Az = {avg_az:+.3f} g  →  {'PASS ✓' if ok else 'FAIL ✗'}")
    return ok


def print_banner():
    print("=" * 60)
    print("  MPU6050 Test  |  Raspberry Pi 4")
    print("=" * 60)


def main():
    print_banner()

    # ── 1. Open I2C bus ───────────────────────────────────────────────────────
    print(f"\n[1] Opening I2C bus {I2C_BUS} …")
    try:
        bus = smbus2.SMBus(I2C_BUS)
    except Exception as e:
        print(f"    [ERROR] Cannot open bus: {e}")
        print("    Ensure I2C is enabled: sudo raspi-config → Interface Options → I2C")
        sys.exit(1)
    print("    Bus opened OK")

    # ── 2. WHO_AM_I check ─────────────────────────────────────────────────────
    print(f"\n[2] Checking WHO_AM_I register (expect 0x68) …")
    try:
        who = bus.read_byte_data(MPU6050_ADDR, WHO_AM_I)
    except OSError as e:
        print(f"    [ERROR] No device at 0x{MPU6050_ADDR:02X}: {e}")
        print("    Check wiring and run: sudo i2cdetect -y 1")
        sys.exit(1)

    if who == 0x68:
        print(f"    WHO_AM_I = 0x{who:02X}  →  MPU6050 detected ✓")
    else:
        print(f"    WHO_AM_I = 0x{who:02X}  →  Unexpected value (possible wiring issue)")

    # ── 3. Initialise ─────────────────────────────────────────────────────────
    print("\n[3] Initialising sensor …")
    init_mpu6050(bus)
    time.sleep(0.1)
    print("    Done")

    # ── 4. Self-test ──────────────────────────────────────────────────────────
    print("\n[4] Running basic self-test (keep sensor flat & still) …")
    run_self_test(bus)

    # ── 5. Live data stream ───────────────────────────────────────────────────
    print("\n[5] Streaming live sensor data  (Ctrl-C to stop)\n")
    header = (
        f"{'Ax(g)':>9} {'Ay(g)':>9} {'Az(g)':>9}"
        f"  │  {'Gx(°/s)':>9} {'Gy(°/s)':>9} {'Gz(°/s)':>9}"
        f"  │  {'Temp(°C)':>9}"
    )
    print(header)
    print("─" * len(header))

    try:
        while True:
            d = read_all(bus)
            print(
                f"{d['ax']:>+9.3f} {d['ay']:>+9.3f} {d['az']:>+9.3f}"
                f"  │  {d['gx']:>+9.3f} {d['gy']:>+9.3f} {d['gz']:>+9.3f}"
                f"  │  {d['temp']:>9.2f}"
            )
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    finally:
        bus.close()
        print("I2C bus closed. Goodbye!")


if __name__ == "__main__":
    main()
