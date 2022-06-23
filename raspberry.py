"""Functions related to the Raspberry Pi & GPIO"""

import datetime
import math
import time
import csv
import os
import shutil
import sys
from copy import copy
import json

import numpy
from scipy.special import erfc

import RPi.GPIO as GPIO

import meas
from ds18b20 import DS18B20

import json

# Import config
if not os.path.exists("config.json"):
    shutil.copyfile("config.example.json", "config.json")

with open("config.json") as json_data_file:
    config = json.load(json_data_file)

RPM1_PIN = config["rpm"]["rpm1"]["pin"]
RPM2_PIN = config["rpm"]["rpm2"]["pin"]
VALVE_PIN = config["valve"]["pin"]
TEMPERATURE_PIN = config["temperature"]["pin"]

session_id = None
last_sensor_reading = 1.0   # Time of last sensor reading
read_interval = None        # Time between sensor readings
temperature_class = DS18B20()
temperature_sensors = temperature_class.device_count()

temperature_vars = [None, None, None]

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

    global session_id, rpm_vars, temperature_vars, last_sensor_reading, read_interval

    read_interval = time.time() - last_sensor_reading  # In seconds, with more detail in decimal

    previous_rpm1 = rpm_vars[0]["previous_rpm"]
    previous_rpm2 = rpm_vars[1]["previous_rpm"]
    current_rpm1 = read_rpm(1)
    current_rpm2 = read_rpm(2)
    pressure_1 = read_pressure(1)
    pressure_2 = read_pressure(2)
    current_temperature1 = read_temperature(1)
    current_temperature2 = read_temperature(2)
    current_temperature3 = read_temperature(3)
    
    # Check if we have to start a new session
    if (previous_rpm1 == 0 and previous_rpm2 == 0 and (current_rpm1 > 0 or current_rpm2 > 0) and session_id == None):
        start_session()

    sensor_data = {
        'sessionId': session_id,
        'rpm': current_rpm1, 
        'rpm2': current_rpm2,
        'temperature': temperature_vars[0] if current_temperature1 == None else current_temperature1,     # Inlet temperature
        'temperature2': temperature_vars[1] if current_temperature2 == None else current_temperature2,    # Outlet temperature
        'temperature3': temperature_vars[2] if current_temperature3 == None else current_temperature3,    # Ambient temperature
        'pressure': pressure_1['pressure'],
        'pressureRelative': None if pressure_1['pressure'] == None else pressure_1['pressure'] - config["pressure"]["pressure1"]["offset"],
        'pressure2': pressure_2['pressure'],
        'pressure2Relative': None if pressure_2['pressure'] == None else pressure_2['pressure'] - config["pressure"]["pressure2"]["offset"]
    }

    # Only write sensor data if there is an active session
    if session_id is not None:
        write_sensor_data(sensor_data)

    # Check if we have to end this session
    if ((previous_rpm1 > 0 or previous_rpm2 > 0) and current_rpm1 == 0 and current_rpm2 == 0 and session_id is not None):
        stop_session()

    rpm_vars[0]["previous_rpm"] = current_rpm1
    rpm_vars[1]["previous_rpm"] = current_rpm2
    temperature_vars[0] = sensor_data["temperature"]
    temperature_vars[1] = sensor_data["temperature2"]
    temperature_vars[2] = sensor_data["temperature3"]

    last_sensor_reading = time.time()  # Current timestamp in seconds (float, so more detail after dot)

    return sensor_data


def write_sensor_data(sensor_data):
    """Write sensor data to a CSV file on the SD card for later analysis"""

    sensor_data_copy = copy(sensor_data)
    sensor_data_copy.pop('sessionId', None)  # Remove sessionId, as we don't need it inside the CSV

    # Add additional data to the log file
    temperature = 0 if sensor_data_copy['temperature'] == None else sensor_data_copy['temperature']
    temperature2 = 0 if sensor_data_copy['temperature2'] == None else sensor_data_copy['temperature2']
    pressure = 0 if sensor_data_copy['pressureRelative'] == None else sensor_data_copy['pressureRelative']
    pressure2 = 0 if sensor_data_copy['pressure2Relative'] == None else sensor_data_copy['pressure2Relative']
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


def read_pressure(sensor = 1):
    """Read pressure from MEAS M32JM sensor

    Temperature returned is only used for internal calibration of the sensor, and is NOT
    the temperature of the medium, but is the temperature of the sensor's membrane

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


def read_temperature(sensor = 1):
    """Read DS18B20 temperature sensors

    Args:
        sensor (int): Which of the DS18B20 sensors to read (1, 2, or 3)

    Returns:
        float: temperature in ºC, or None if sensor index is out of range
    """
    
    global temperature_class, temperature_sensors

    i = sensor - 1

    return temperature_class.tempC(i) if i < temperature_sensors else None


def open_valve():
    """Open an electronic valve to start a test session"""

    GPIO.output(VALVE_PIN, GPIO.HIGH)

    return { "valveOpen": True }


def close_valve():
    """Close an electronic valve to stop a test session"""

    GPIO.output(VALVE_PIN, GPIO.LOW)

    return { "valveOpen": False }


def start_session():
    """Start a test session"""
    print("In start_session()", file=sys.stderr)

    global session_id

    # We'll set time in UTC until we allow users to specify their timezone
    session_start = datetime.datetime.now(datetime.timezone.utc)
    session_id = session_start.strftime("%Y-%m-%d_%H.%M.%S")

    return { "session": session_id }


def stop_session():
    """Stop a test session"""

    global session_id

    session_id = None

    return { "session": session_id }

  
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
        for index, pressure in enumerate(pressures):
            i = str(index + 1)
            configFile['pressure']['pressure' + i]['offset'] = pressures[index]

        # Write it back to the file
        with open('config.json', 'w') as f:
            json.dump(configFile, f)

        # Set new values in global config object
        config = configFile 

    #except Exception as e:
        #print("Error zeroing pressure: %s" % e, file=sys.stderr)
    except 0:
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