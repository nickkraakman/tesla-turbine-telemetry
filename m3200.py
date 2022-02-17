"""Methods to read data from a MEAS M32JM pressure & temperature sensor"""

import sys
import time
import pigpio

# Define variables
temp = []
I2C_ERR = 0
temperature = pressure = float(0)
Pmax = float(100)  # 100 PSI, should be defined by the sensor pressure range.
Pmin = float(0)
Tscope = 200  # -50~150
Tspan = 2048  # 11 bit
Pvalue = Tvalue = 0
P1 = 1000  # 1000 counts is 0% pressure = 0 psi = 0 bar
P2 = 15000  # 15000 counts is 100% pressure = 100 psi = 7 bar
Pspan = P2 - P1

SENSOR_ADDRESS = 0x28  # 0101000-, check datasheet or run `sudo i2cdetect -y 1`


def read_sensor(sensor = 1):
    pi = pigpio.pi()

    if not pi.connected:
        print("No Pi found", file=sys.stderr)
        exit()

    bus = 1 if sensor == 1 else 3  # Original I2C bus 1, custom I2C bus 3, where GPIO 23 = SDA and GPIO 24 = SCL
    handle = pi.i2c_open(bus, SENSOR_ADDRESS)

    # Check if we're properly connected to the sensor
    if (handle < 0):
        print("Error connecting to the sensor", file=sys.stderr)
        pi.stop()
        exit()

    pi.i2c_write_quick(handle, 1)  # Send READ_MR command to start measurement and DSP calculation cycle
    time.sleep(2 / 1000)  # Response time from power on to reading measurement data is 8.4 ms with sleep mode

    count, data = pi.i2c_read_device(handle, 4)  # Send READ_DF4 command, to fetch 2 pressure bytes & 2 temperature bytes

    pi.i2c_close(handle)
    pi.stop()

    print("count = ", count)
    print("data = ", data)

    if count < 0:
        print("Error reading from the sensor", file=sys.stderr)
        pi.stop()
        exit()

    print("data[0] =", "{:08b}".format(data[0]) )  # First two bits are status bits
    print("data[1] =", "{:08b}".format(data[1]) )
    print("data[2] =", "{:08b}".format(data[2]) )
    print("data[3] =", "{:08b}".format(data[3]) )  # Last 5 bits are unrelated and should be ignored

    # @TODO: handle each status
    statusCode = "{:08b}".format(data[0])[:2]
    print("Status code =", statusCode)

    if statusCode == "00":
        print("Status: Normal operation")
    elif statusCode == "01":
        print("Status: Reserved", file=sys.stderr)
    elif statusCode == "10":
        print("Status: Stale data", file=sys.stderr)
    else:
        print("Status: Fault detected", file=sys.stderr)

    Pvalue = (data[0] << 8) | data[1]
    Tvalue = (data[2] << 3) | (data[3] >> 5)

    print("Pvalue =", Pvalue)
    print("Tvalue =", Tvalue)

    temperature = Tvalue * Tscope / Tspan - 50
    pressure = (Pvalue + 1000) * (Pmax - Pmin) / Pspan + Pmin  # 100L

    print("Temperature =", temperature, "ºC")  # Temperature in ºC
    print("Pressure =", pressure, "PSI")  # Pressure in PSI (atmospheric is 14.69)

    return {
        "temperature": temperature,
        "pressure": pressure
    }