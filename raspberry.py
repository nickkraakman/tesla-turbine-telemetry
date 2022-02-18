"""Functions related to the Raspberry Pi & GPIO"""

import datetime
import time
import csv
import os
import sys

import RPi.GPIO as GPIO

import meas

import random  # REMOVE once all sensor functions are fully implemented

TACHO_PIN = 4
VALVE_PIN = 21

session_id = None
previous_rpm = -1  # We'll instantiate with -1 instead of 0 to prevent accidental session start trigger
period = 0  # Time between RPM sensor triggers in ns
last_trigger = 0  # Time of last RPM sensor trigger in ns


def do_action(action, payload = None):
    """Run the function that has the same name as the action parameter"""
    function = globals()[action] if action in globals() else None

    if function is None:
        response = { "error": "Function " + action + " does not exist" }
    elif payload is None:
        response = function()
    else:
        response = function(payload)

    return response


def read_sensors():
    """Read all sensors attached to the Raspberry Pi and return their values."""
    print( 'Reading sensor data' )

    global session_id, previous_rpm

    current_rpm = read_rpm(1)
    temp_pressure_1 = read_temp_and_pressure(1)
    temp_pressure_2 = read_temp_and_pressure(2)

    # Check if we have to start a new session
    if previous_rpm == 0 and current_rpm > 0:
        # We'll set time in UTC until we allow users to specify their timezone
        session_start = datetime.datetime.now(datetime.timezone.utc)
        session_id = session_start.strftime("%Y-%m-%d_%H.%M.%S")

    sensor_data = {
        'sessionId': session_id,
        'rpm': current_rpm, 
        'rpm2': read_rpm(2),
        'temperature': temp_pressure_1['temperature'],
        'temperature2': temp_pressure_2['temperature'],
        'pressure': temp_pressure_1['pressure'],
        'pressure2': temp_pressure_2['pressure']
    }

    # Only write sensor data if there is an active session
    if session_id is not None:
        write_sensor_data(sensor_data)

    # Check if we have to end this session
    if previous_rpm > 0 and current_rpm == 0:
        session_id = None

    previous_rpm = current_rpm

    return sensor_data


def write_sensor_data(sensor_data):
    """Write sensor data to a CSV file on the SD card for later analysis"""

    sensor_data.pop('sessionId', None)  # Remove sessionId, as we don't need it inside the CSV

    file_path = './sessions/' + session_id + '.csv'

    os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directory if not exist

    try:
        # Create file if not exist, else append new data
        with open(file_path, 'a') as csv_file:
            csv_columns = list(sensor_data)  # Use keys as column names
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            
            # Write header if we're at the first line of the file
            if csv_file.tell() == 0:
                writer.writeheader()

            writer.writerow(sensor_data)

    except IOError:
        print("Error writing to CSV file", file=sys.stderr)
        return False

    return True


def read_rpm(sensor = 1):
    """Determine RPM from period of one rotation in ns
    
    Args:
        sensor (int): Which RPM to read (1 or 2)

    Returns: 
        int: RPM
    """

    global period, last_trigger

    # Check if the last trigger time was > 2 seconds ago, if so, rotor has stopped, so set RPM to 0
    time_now = time.time_ns()
    if time_now - last_trigger > (2 * 1000 * 1000 * 1000):
        rpm = 0
    elif sensor == 1:
        rpm = 60 * (1 * 1000 * 1000 * 1000) / period if period > 0 else 0
    else:
        rpm = random.randrange(10000, 200000)  # @TODO: implement reading second RPM

    return round(rpm)


def read_temp_and_pressure(sensor = 1):
    """Read temperature & pressure from MEAS M32JM sensor

    Args:
        sensor (int): Which of the M32JM sensors to read (1 or 2)

    Returns: 
        dict: Contains "temperature" and "pressure", whose values are None on error.

        Example return::
            {
                "temperature": temperature in ºC,
                "pressure": pressure in PSI
            }
    """

    response = meas.read_m3200(sensor)

    if response == None:
        # An error occurred, return empty response
        response = {
            "temperature": None,
            "pressure": None
        }

    return response


def open_valve():
    """Open an electronic valve to start a test session"""

    GPIO.output(VALVE_PIN, GPIO.HIGH)

    return { "valveOpen": True }


def close_valve():
    """Close an electronic valve to stop a test session"""

    GPIO.output(VALVE_PIN, GPIO.LOW)

    return { "valveOpen": False }


def tacho_callback(channel):
    """Called by pin interrupt on each rotation"""
    global period, last_trigger

    time_now = time.time_ns()
    period = time_now - last_trigger
    last_trigger = time_now


def init():
    """Setup sensor pins"""
    GPIO.setmode(GPIO.BCM) # Use Broadcom GPIO pin numbering

    # GPIO 4 is the one we want to count.  Set it up
    # as an input, no pull-up/down required.
    GPIO.setup(TACHO_PIN, GPIO.IN)
    GPIO.setup(VALVE_PIN, GPIO.OUT, initial=GPIO.LOW)

    # When a falling edge is detected on TACHO_PIN run the callback
    GPIO.add_event_detect(TACHO_PIN, GPIO.FALLING, callback=tacho_callback)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:  # Keyboard interrupt will never be used, consider using atexit.register() instead
        print ("   Quit")
        GPIO.cleanup()