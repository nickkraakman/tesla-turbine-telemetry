import datetime
import csv
import os

session_id = None
previous_rpm = -1  # We'll instantiate with -1 instead of 0 to prevent accidental session start trigger


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

    global session_id
    global previous_rpm

    current_rpm = read_rpm()

    # Check if we have to start a new session
    if previous_rpm == 0 and current_rpm > 0:
        # We'll set time in UTC until we allow users to specify their timezone
        session_start = datetime.datetime.now(datetime.timezone.utc)
        session_id = session_start.strftime("%Y-%m-%d_%H.%M.%S")

    sensor_data = {
        'sessionId': session_id,
        'rpm': current_rpm, 
        'temperature': read_temperature()
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
        print("Error writing to CSV file")
        return False

    return True


def read_rpm():
    """Read RPM sensor"""

    return 234000


def read_temperature():
    """Read temperature sensor(s)"""

    return 23


def open_valve():
    """Open an electronic valve to start a test session"""

    return { "valveOpen": True }


def close_valve():
    """Close an electronic valve to stop a test session"""

    return { "valveOpen": False }