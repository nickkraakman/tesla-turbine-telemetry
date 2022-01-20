def read_sensors():
    """Read all sensors attached to the Raspberry Pi and return their values."""
    print( 'Reading sensor data' )

    sensor_data = {
        'rpm': read_rpm(), 
        'temperature': read_temperature()
    }

    log_sensor_data(sensor_data)

    return sensor_data


def log_sensor_data(sensor_data):
    """Write sensor data to a CSV file on the SD card for later analysis"""

    return True


def read_rpm():
    """Read RPM sensor"""

    return 234000


def read_temperature():
    """Read temperature sensor(s)"""

    return 23