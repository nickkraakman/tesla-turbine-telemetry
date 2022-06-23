"""Methods to read data from a MEAS M32JM pressure & temperature sensor"""

import sys
import time
import subprocess

import pigpio


# Define variables
temperature = pressure = float(0)
Pmax = float(100)  # 100 PSI, should be defined by the sensor pressure range.
Pmin = float(0)
Tscope = 200  # -50~150
Tspan = 2048  # 11 bit
Pvalue = Tvalue = 0
P1 = 1000  # 1000 counts is 0% pressure = 0 psi = 0 bar
P2 = 15000  # 15000 counts is 100% pressure = 100 psi = 7 bar
Pspan = P2 - P1

SENSOR_ADDRESS = 0x28  # 7 bit address 0101000-, check datasheet or run `sudo i2cdetect -y 1`


def read_m3200(sensor = 1):
    """Read temperature and pressure from M32JM sensor

    Args:
        sensor (int): Which of the M32JM sensors to read (1 or 2)

    Returns: 
        dict: Contains "temperature" and "pressure" if successful, None otherwise.
        
        Example return::
            {
                "temperature": temperature in ºC,
                "pressure": pressure in PSI
            }
    """
    pi = pigpio.pi()

    if not pi.connected:
        print("No Pi found", file=sys.stderr)
        return None

    bus = 1 if sensor == 1 else 3  # Original I2C bus = 1, custom I2C bus = 3, where GPIO 23 = SDA and GPIO 24 = SCL
    handle = pi.i2c_open(bus, SENSOR_ADDRESS)

    # Check if we're properly connected to the sensor
    if (handle < 0):
        print("Error connecting to the sensor on bus %s" % bus, file=sys.stderr)
        pi.stop()
        return None

    # Attempt to write to the sensor, catch exceptions
    try:
      pi.i2c_write_quick(handle, 1)  # Send READ_MR command to start measurement and DSP calculation cycle
    except:
      #print("Error writing to the sensor, perhaps none is connected to bus %s" % bus, file=sys.stderr)
      pi.stop()
      return None

    time.sleep(2 / 1000)  # Response time from power on to reading measurement data is 8.4 ms with sleep mode

    bytes_to_read = 2

    count, data = pi.i2c_read_device(handle, bytes_to_read)  # Send READ_DF2 command, to fetch 2 pressure bytes
    #count, data = pi.i2c_read_device(handle, 4)  # Send READ_DF4 command, to fetch 2 pressure bytes & 2 temperature bytes

    pi.i2c_close(handle)
    pi.stop()

    print("count = ", count)
    print("data = ", data)

    if count < 0:
        print("Error reading from the sensor on bus %s" % bus, file=sys.stderr)
        subprocess.run(["/usr/sbin/i2cdetect", "-y", str(bus)])  # Running the i2cdetect command tends to solve this error on the next call
        return None

    print("data[0] =", "{:08b}".format(data[0]) )  # First two bits are status bits, other 6 bits are pressure bits
    print("data[1] =", "{:08b}".format(data[1]) )  # All bits are pressure bits   
    
    if (bytes_to_read == 4):
        print("data[2] =", "{:08b}".format(data[2]) )  # All bits are temperature bits
        print("data[3] =", "{:08b}".format(data[3]) )  # First 3 bits are temperature bits, last 5 bits are unrelated and should be ignored

    # Handle sensor status
    status_code = "{:08b}".format(data[0])[:2]  # Get first two bits from first byte
    print("Status code =", status_code)

    if status_code == "00":
        print("Status: Normal operation")
    elif status_code == "01":
        print("Status: Reserved", file=sys.stderr)
        return None
    elif status_code == "10":
        print("Status: Stale data", file=sys.stderr)
        return None
    else:
        print("Status: Fault detected", file=sys.stderr)
        return None

    # Perform some bitwise magic to get the the temperature count and the pressure count
    Pvalue = (data[0] << 8) | data[1]
    print("Pvalue =", Pvalue)

    pressure = (Pvalue + 1000) * (Pmax - Pmin) / Pspan + Pmin
    print("Pressure =", pressure, "PSI")  # Pressure in PSI (atmospheric is ~14.69, 0 is perfect vacuum, but this sensor only goes down to 7.14 PSI...)

    if (bytes_to_read == 4):
        Tvalue = (data[2] << 3) | (data[3] >> 5)
        print("Tvalue =", Tvalue)

        temperature = Tvalue * Tscope / Tspan - 50
        print("Temperature =", temperature, "ºC")  # Temperature in ºC = INTERNAL temperature used for calibration, NOT temperature of the medium unfortunately
    else: 
        temperature = None
    
    return {
        "temperature": temperature,
        "pressure": pressure
    }