"""Functions related to the Raspberry Pi & GPIO"""

import datetime
import math
import time
import csv
import os
import sys
from copy import copy
import json

import numpy
from scipy.special import erfc

import RPi.GPIO as GPIO

import meas

import json

# Import config
if not os.path.exists("config.json"):
    os.rename("config.example.json", "config.json")

with open("config.json") as json_data_file:
    config = json.load(json_data_file)

RPM1_PIN = config["rpm"]["rpm1"]["pin"]
RPM2_PIN = config["rpm"]["rpm2"]["pin"]
VALVE_PIN = config["valve"]["pin"]

# For relative pressure, we set ambient to zero Psi using an offset
pressure1_adjustment = 0 if config["pressure"]["measurementType"] == "absolute" else config["pressure1"]["offset"]
pressure2_adjustment = 0 if config["pressure"]["measurementType"] == "absolute" else config["pressure2"]["offset"]

session_id = None
last_sensor_reading = 1.0   # Time of last sensor reading
read_interval = None        # Time between sensor readings

rpm_vars_model = {
    "previous_rpm": -1,     # We'll instantiate with -1 instead of 0 to prevent accidental session start trigger
    "last_trigger": 0,      # Time of last RPM sensor trigger in ns
    "periods": [],          # Times between RPM sensor triggers in ns
}

rpm_vars = [rpm_vars_model.copy(), rpm_vars_model.copy()]  # We're tracking data for 2 RPM sensors


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

    global session_id, rpm_vars, last_sensor_reading, read_interval, pressure1_adjustment, pressure2_adjustment

    read_interval = time.time() - last_sensor_reading  # In seconds, with more detail in decimal

    previous_rpm1 = rpm_vars[0]["previous_rpm"]
    previous_rpm2 = rpm_vars[1]["previous_rpm"]
    current_rpm1 = read_rpm(1)
    current_rpm2 = read_rpm(2)
    temp_pressure_1 = read_temp_and_pressure(1)
    temp_pressure_2 = read_temp_and_pressure(2)

    # Check if we have to start a new session
    if (previous_rpm1 == 0 and previous_rpm2 == 0 and (current_rpm1 > 0 or current_rpm2 > 0) and session_id == None):
        # We'll set time in UTC until we allow users to specify their timezone
        session_start = datetime.datetime.now(datetime.timezone.utc)
        session_id = session_start.strftime("%Y-%m-%d_%H.%M.%S")

    sensor_data = {
        'sessionId': session_id,
        'rpm': current_rpm1, 
        'rpm2': current_rpm2,
        'temperature': temp_pressure_1['temperature'],
        'temperature2': temp_pressure_2['temperature'],
        'pressure': temp_pressure_1['pressure'] - pressure1_adjustment,
        'pressure2': temp_pressure_2['pressure'] - pressure2_adjustment
    }

    # Only write sensor data if there is an active session
    if session_id is not None:
        write_sensor_data(sensor_data)

    # Check if we have to end this session
    if ((previous_rpm1 > 0 or previous_rpm2 > 0) and current_rpm1 == 0 and current_rpm2 == 0 and session_id is not None):
        session_id = None

    rpm_vars[0]["previous_rpm"] = current_rpm1
    rpm_vars[1]["previous_rpm"] = current_rpm2

    last_sensor_reading = time.time()  # Current timestamp in seconds (float, so more detail after dot)

    return sensor_data


def write_sensor_data(sensor_data):
    """Write sensor data to a CSV file on the SD card for later analysis"""

    global pressure1_adjustment, pressure2_adjustment

    sensor_data_copy = copy(sensor_data)
    sensor_data_copy.pop('sessionId', None)  # Remove sessionId, as we don't need it inside the CSV

    # Add additional data to the log file
    temperature = 0 if sensor_data_copy['temperature'] == None else sensor_data_copy['temperature']
    temperature2 = 0 if sensor_data_copy['temperature2'] == None else sensor_data_copy['temperature2']
    pressure = 0 if sensor_data_copy['pressure'] == None else sensor_data_copy['pressure'] - pressure1_adjustment
    pressure2 = 0 if sensor_data_copy['pressure2'] == None else sensor_data_copy['pressure2'] - pressure2_adjustment
    timestamp_now_utc = datetime.datetime.now(datetime.timezone.utc)
    formatted_time_now_utc = timestamp_now_utc.strftime("%Y-%m-%d %H:%M:%S")

    sensor_data_copy['temperatureDiff'] = numpy.diff([temperature, temperature2])[0]  # Temperature difference
    sensor_data_copy['pressureDiff'] = numpy.diff([pressure, pressure2])[0]           # Pressure difference
    sensor_data_copy['time'] = formatted_time_now_utc                                 # Time

    file_path = './sessions/' + session_id + '.csv'

    os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directory if not exist

    try:
        # Create file if not exist, else append new data
        with open(file_path, 'a') as csv_file:
            csv_columns = list(sensor_data_copy)  # Use keys as column names
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)

            # Write header if we're at the first line of the file
            if csv_file.tell() == 0:
                writer.writeheader()

            writer.writerow(sensor_data_copy)

    except IOError:
        print("Error writing to CSV file", file=sys.stderr)
        return False

    return True


def filter_outliers(datapoints):
    """Run Chauvenet's Criterion to remove outliers
    @See: https://www.statisticshowto.com/chauvenets-criterion/
    @See: https://github.com/msproteomicstools/msproteomicstools/blob/master/msproteomicstoolslib/math/chauvenet.py

    Args:
        datapoints (list): Array of datapoints from which to filter the outliers

    Returns:
        list: Valid datapoints with outliers removed
    """
    # Check if list is empty to prevent division by zero errors
    if not datapoints:
        return datapoints

    criterion = 1.0/(2*len(datapoints))
    valid_datapoints = []

    # Step 1: Determine sample mean
    mean = numpy.mean(datapoints)

    # Step 2: Calculate standard deviation of sample
    standard_deviation = numpy.std(datapoints)

    # Step 3: For each value, calculate distance to mean in standard deviations
    # Compare to criterion and store those that pass in valid_periods array
    for datapoint in datapoints:
        distance = abs(datapoint-mean)/standard_deviation  # Distance of a value to mean in stdv's
        distance /= 2.0**0.5                               # The left and right tail threshold values
        probability = erfc(distance)                       # Area normal distribution
        if probability >= criterion:
            valid_datapoints.append(datapoint)             # Store only non-outliers
    
    return valid_datapoints


def read_rpm(sensor = 1):
    """Determine RPM from period of one rotation in ns
    
    Args:
        sensor (int): Which RPM to read (1 or 2)

    Returns: 
        int: RPM
    """

    global rpm_vars

    i = sensor - 1
    periods = rpm_vars[i]["periods"]
    last_trigger = rpm_vars[i]["last_trigger"]

    valid_periods = filter_outliers(periods)

    # Check if the last trigger time was > 2 seconds ago, if so, rotor has stopped, so set RPM to 0
    time_now = time.time_ns()
    if time_now - last_trigger > (2 * 1000 * 1000 * 1000):
        rpm = 0
    else:
        valid_mean_period = numpy.mean(valid_periods)

        # If we have way less samples than expected based on the length of the mean period, 
        # we're probably dealing with a spike due to vibrations, which should be ignored
        expected_samples = read_interval / (valid_mean_period / (1 * 1000 * 1000 * 1000))  # Number of samples we can expect at the mean period over the read interval
        if math.isnan(expected_samples) or len(periods) < (expected_samples / 3):  # / 3 to give a margin of safety if sensor doesn't trigger each time it should
            rpm = 0
        else:
            rpm = 60 * (1 * 1000 * 1000 * 1000) / valid_mean_period if valid_mean_period > 0 else 0

    # Reset RPM periods array so we can calculate a new average
    rpm_vars[i]["periods"] = []

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


def zero_pressure(pressures = []):
    """Set ambient pressure to zero by setting the offset in the config
    
    Args:
        pressures (list): Array pressures

    Returns:
        bool: True if success, False if an error occurred
    """

    global config

    try:
        with open('config.json', 'r') as f:
            configFile = json.load(f)

        # Edit the data if enough datapoints are sent
        if(len(pressures) < 2):
            print("Unable to zero, <2 pressures received", file=sys.stderr)
            return False

        configFile['pressure']['pressure1']['offset'] = pressures[0]
        configFile['pressure']['pressure2']['offset'] = pressures[1]

        # Write it back to the file
        with open('config.json', 'w') as f:
            json.dump(configFile, f)

        # Set new values in global config object
        config = configFile 

    except:
        print("Error zeroing pressure", file=sys.stderr)
        return False

    return True


def tacho_callback(channel):  # Channel = GPIO pin number
    """Called by pin interrupt on each rotation"""
    global rpm_vars

    sensor = 1 if channel == RPM1_PIN else 2
    i = sensor - 1

    last_trigger = rpm_vars[i]["last_trigger"]

    time_now = time.time_ns()
    rpm_vars[i]["periods"].append(time_now - last_trigger)
    rpm_vars[i]["last_trigger"] = time_now


def init():
    """Setup sensor pins"""
    GPIO.setmode(GPIO.BCM) # Use Broadcom GPIO pin numbering

    # GPIO 4 is the one we want to count.  Set it up
    # as an input, no pull-up/down required.
    GPIO.setup(RPM1_PIN, GPIO.IN)
    GPIO.setup(RPM2_PIN, GPIO.IN)
    GPIO.setup(VALVE_PIN, GPIO.OUT, initial=GPIO.LOW)

    # When a falling edge is detected on TACHO_PIN run the callback
    GPIO.add_event_detect(RPM1_PIN, GPIO.FALLING, callback=tacho_callback)
    GPIO.add_event_detect(RPM2_PIN, GPIO.FALLING, callback=tacho_callback)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:  # Keyboard interrupt will never be used, consider using atexit.register() instead
        print ("   Quit")
        GPIO.cleanup()