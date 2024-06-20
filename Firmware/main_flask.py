"""
File: main.py
Description: This script runs the main program for the Standup Desk Sensor.
Author: Sami Kaab
Date: 2023-07-05
"""
import time
import os
import glob


import threading
from collections import deque
from flask import Flask, jsonify,request,render_template, session,redirect, url_for,Response
from flask_session import Session
import datetime
import configparser
from waitress import serve
import json
import subprocess



import lib.SDL_DS3231 as RTC
import backup_to_drive as google_drive
from lib.battery import compute_battery_level

from shared_resources import stop_event, CONFIG_FILE, TEMP_DIR, DEVICE_ID, DATA_DIR
from sensor_thread import read_write_loop
from upload_thread import upload_loop
from led_thread import pulsate_led

sensor_data_queue = deque(maxlen=10)
status_queue = deque(maxlen=10)
sensor_datetime = []
sensor_presence = []
sensor_distance = []


def internet_check_loop(led_status_queue):
    """ Checks if the internet is available and updates the led_status_queue accordingly

    Args:
        led_status_queue (deque): A queue that contains the status of the device for the led thread.
    """
    while True:
        try:
            connected = google_drive.is_internet_available()
            led_status_queue.append(("connected", connected))
        except:
            pass
        time.sleep(5)   
    print("Internet check thread stopped")


def add_wifi_config(ssid, encryption, key):
    """Adds a new wifi config to the wireless file

    Args:
        ssid (str): The ssid of the wifi network
        encryption (str): The encryption type of the wifi network
        key (str): The password of the wifi network
    """
    wifi_config = (
        'config wifi-config\n'
        f'\toption key \'{key}\'\n'
        f'\toption ssid \'{ssid}\'\n'
        f'\toption encryption \'{encryption}\'\n'
        '\n'
    )

    with open('/etc/config/wireless', 'a') as f:
        f.write(wifi_config)

    
def delete_wifi_config(ssid):
    """
    Deletes the wifi configuration for the given SSID from the wireless configuration file.

    Args:
        ssid (str): The SSID of the wifi configuration to be deleted.

    """
    with open('/etc/config/wireless', 'r') as f:
        lines = f.readlines()

    # Find and remove the wifi-config section
    new_lines = []
    lineIndex = 0
    while lineIndex < len(lines):
        if lines[lineIndex].startswith('config wifi-config') and ssid in lines[lineIndex + 2]:
            lineIndex += 4
        if lineIndex < len(lines):
            new_lines.append(lines[lineIndex])
            lineIndex += 1

    # Write the modified content back to the file
    with open('/etc/config/wireless', 'w') as f:
        f.writelines(new_lines)

def cleanup_expired_sessions(session_dir):
    """
    Deletes expired session files from the given directory.

    Args:
        session_dir (str): The path to the directory containing the session files.
    """
    now = datetime.datetime.now()
    for session_file in glob.glob(os.path.join(session_dir, '*')):
        file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(session_file))
        if now - file_timestamp > app.config['PERMANENT_SESSION_LIFETIME']:
            os.remove(session_file)


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = 'flask_session'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)  # Set the session timeout to 30 minutes
cleanup_expired_sessions(app.config['SESSION_FILE_DIR'])
Session(app)

            
@app.before_request
def check_session_timeout():
    """Checks if the session has timed out and resets the user_role if it has.
    """
    if 'user_role' in session:
        if 'last_login' not in session:
            pass
        elif (datetime.datetime.now() - session['last_login']).total_seconds() > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
            # Session timeout reached; reset user_role
            session['user_role'] = None


@app.route('/')
def home():
    return render_template('login.html')

# SSE route to send real-time data to the client
@app.route('/update_data', methods=['GET'])
def update_data():
    """Sends the latest sensor data to the client

    Returns:
        JSON: A JSON object containing the latest sensor data
    """
    if len(sensor_data_queue):
        while len(sensor_data_queue):
            # Get the latest data from the queue
            sensor_data = sensor_data_queue.popleft()
            # Send both datetime and distance value to the client
            datetime_str = sensor_data[0].strftime("%Y-%m-%d %H:%M:%S")  # Format datetime as a string
            # append the new data to the sensor lists and shift data if the list is longer than 10
            sensor_datetime.append(datetime_str)
            sensor_distance.append(sensor_data[1])
            sensor_presence.append(sensor_data[2])
            if len(sensor_datetime) > 10:
                sensor_datetime.pop(0)
                sensor_distance.pop(0)
                sensor_presence.pop(0)
                
            

        return jsonify({'datetime': sensor_datetime, 'distance': sensor_distance, 'presence': sensor_presence})
    else:
        return jsonify({'data': None})

@app.route('/get_battery', methods=['GET'])
def get_battery():
    """
        Returns the battery level of the device
    """
    battery_level = int(compute_battery_level())
    return jsonify({'battery_level': battery_level})


@app.route('/button_click', methods=['POST'])
def button_click():
    """
    Handles the button click event

    Returns:
        JSON: A JSON object containing the action to be taken
    """
    data = request.json
    action = data.get('action')

    if action == 'start':
        print("start")
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        config.set('DEFAULT', 'STOPPED', 'false')
        with open(CONFIG_FILE, 'w') as configfile:
                    config.write(configfile)
        stop_event.clear()
    elif action == 'stop':
        print("stop")
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        config.set('DEFAULT', 'STOPPED', 'true')
        stop_event.set()
        with open(CONFIG_FILE, 'w') as configfile:
                    config.write(configfile)

    return jsonify({'message': f'Button pressed for action: {action}'})

@app.route('/get_device_info', methods=['GET'])
def get_device_id():
    """
        Returns the device ID
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    ID = config.get('DEFAULT', 'ID')
    SAMPLING_PERIOD = config.getint('DEFAULT', 'SAMPLING_PERIOD')
    WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
    SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
    if status_queue:
        status = status_queue.popleft()
    
    return jsonify({'ID': ID, 'SP': SAMPLING_PERIOD, 'WAKE_AT': WAKE_AT, 'SLEEP_AT': SLEEP_AT, 'STATUS': status})


@app.route('/check_password', methods=['POST'])
def check_password():
    """
    Checks if the password entered by the user is correct

    Returns:
        JSON: A JSON object containing a boolean value indicating if the password is correct and the redirect url
    """
    data = request.json
    password = data.get('password')
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    correct_password = config.get('DEFAULT', 'PASSWORD')
    
    if password == correct_password:
        session['user_role'] = 'admin'
        session['last_login'] = datetime.datetime.now()  # Update last_activity for the current request

        return jsonify({'valid': True, 'redirect': url_for('admin_dashboard')})
    else:
        return jsonify({'valid': False})
    



@app.route('/change_password', methods=['POST'])
def change_password():
    """
    Changes the password of the device
    
    Returns:
        JSON: A JSON object containing a boolean value indicating if the password is correct and the redirect url   
    """
        
    data = request.get_json()
    print(data)
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    correct_password = config.get('DEFAULT', 'PASSWORD')
    new_password = data["newPassword"]
    
    if data['oldPassword'] == correct_password:
        print(f"changing password to {new_password}")
        try:
            config.set('DEFAULT', 'PASSWORD', new_password)
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            print(e)
            return jsonify({"status": "error", "message": str(e)})
        try:
            #execute the command: echo -e "new_password\nnew_password" | passwd
            line  = f"echo -e \"{new_password}\\n{new_password}\" | passwd"
            subprocess.run(line, shell=True)
        except Exception as e:
            print(e)
            return jsonify({"status": "error", "message": str(e)})
        # #change the omega2 pro password
        # try:
        #     line = f"uci set wireless.ap.key='{new_password}' && uci commit wireless && /etc/init.d/network restart"
        #     print(f"Wi-Fi password for 'iface 'ap'' updated to: {new_password}")
        #     subprocess.run(line, shell=True)
        # except Exception as e:
        #     print(e)
        #     return jsonify({"status": "error", "message": str(e)})

        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Incorrect password"})

    

@app.route('/session', methods=['GET'])
def get_session():
    """
    Returns the user role of the current session
    
    Returns:
        JSON: A JSON object containing the user role of the current session
    """
    if 'user_role' in session:
        return jsonify({'user_role': session['user_role']})
    else:
        return jsonify({'user_role': None})

@app.route('/dashboard/admin')
def admin_dashboard():
    """
    Renders the admin dashboard page if the user is authenticated as an admin or redirects to the home page if the user is not authenticated
    
    Returns:
        HTML: The HTML page to be rendered with the device configuration
    """
    # Check if the user is authenticated as an admin
    print(f"{session.get('user_role')}")
    if session.get('user_role') == 'admin':
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        ID = config.get('DEFAULT', 'ID')
        SAMPLING_PERIOD = config.getint('DEFAULT', 'SAMPLING_PERIOD')
        WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
        SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
        UPLOAD_PERIOD = config.getint('DEFAULT', 'UPLOAD_PERIOD')
        NEW_FILE_PERIOD = config.getint('DEFAULT', 'NEW_FILE_PERIOD')
        LED_INTENSITY = config.getint('DEFAULT', 'LED_INTENSITY') 
        WRITE_PERIOD = config.getint('DEFAULT', 'WRITE_PERIOD')

        return render_template('admin_dashboard.html', ID=ID, SP=SAMPLING_PERIOD, WAKE_AT=WAKE_AT, SLEEP_AT=SLEEP_AT, UP=UPLOAD_PERIOD, NFP=NEW_FILE_PERIOD, LED_INTENSITY=LED_INTENSITY, WP=WRITE_PERIOD)
    else:
        return redirect(url_for('home'))

@app.route('/dashboard/guest')
def guest_dashboard():
    """
    Renders the guest dashboard page
    
    Returns:
        HTML: The HTML page to be rendered with the device configuration
    """ 
        
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    ID = config.get('DEFAULT', 'ID')
    SAMPLING_PERIOD = config.getint('DEFAULT', 'SAMPLING_PERIOD')
    WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
    SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
    UPLOAD_PERIOD = config.getint('DEFAULT', 'UPLOAD_PERIOD')
    NEW_FILE_PERIOD = config.getint('DEFAULT', 'NEW_FILE_PERIOD')
    LED_INTENSITY = config.getint('DEFAULT', 'LED_INTENSITY') 
    WRITE_PERIOD = config.getint('DEFAULT', 'WRITE_PERIOD')
    return render_template('guest_dashboard.html', ID=ID, SP=SAMPLING_PERIOD, WAKE_AT=WAKE_AT, SLEEP_AT=SLEEP_AT, UP=UPLOAD_PERIOD, NFP=NEW_FILE_PERIOD, LED_INTENSITY=LED_INTENSITY, WP=WRITE_PERIOD)

    
@app.route('/wifi_settings', methods=['GET'])
def get_wifi():
    """
    Returns the list of available wifi networks
    
    Returns:
        JSON: A JSON object containing the list of available wifi networks  
    """
        
    print("get_wifi")
    if session.get('user_role') == 'admin':
        try:
            output = subprocess.check_output(['/usr/bin/wifisetup', 'list'], stderr=subprocess.STDOUT)
            # Parse the JSON output to get a list of networks
            networks = json.loads(output)['results']
        except subprocess.CalledProcessError as e:
            # Handle any errors that occur when running the command
            error_message = e.output
            networks = []  # Set networks to an empty list

        return jsonify({'networks': networks})
    else:   
        return jsonify({'networks': []})

@app.route('/add_wifi', methods=['POST'])
def add_network():
    """
    Adds a new wifi network to the device
    
    Returns:
        JSON: A JSON object containing the status of the operation
    """
        
    # print the form data from the POST request
    print(request.get_json())
    # /usr/bin/wifisetup add -ssid <ssid> -encr <encryption type> -password <password>
    try:
        # print(f"command: /usr/bin/wifisetup add -ssid {request.get_json()['ssid']} -encr {request.get_json()['encryption']} -password {request.get_json()['wifiPassword']}")
        # output  = subprocess.check_output(['/usr/bin/wifisetup', 'add', '-ssid', str(request.get_json()['ssid']), '-encr', str(request.get_json()['encryption']), '-password', str(request.get_json()['wifiPassword'])], stderr=subprocess.STDOUT)
        # output = output.decode('utf-8')
        # print(output)
        add_wifi_config(request.get_json()['ssid'], request.get_json()['encryption'], request.get_json()['wifiPassword'])
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/remove/<ssid>', methods=['POST'])
def remove_network(ssid):
    """
    Removes a wifi network from the device

    Args:
        ssid (str): The SSID of the wifi network to be removed

    Returns:
        JSON: A JSON object containing the status of the operation
    """
    try:
        # output = subprocess.check_output(['/usr/bin/wifisetup', 'remove', '-ssid' , ssid], stderr=subprocess.STDOUT)
        # output = output.decode('utf-8')
        # print(output)
        delete_wifi_config(ssid)
    except:
        pass
    return jsonify({"status": "success"})
    
@app.route('/wifi/apply_changes', methods=['POST'])
def apply_wifi_changes():
    """
    Applies the wifi changes to the device
    
    Returns:
        JSON: A JSON object containing the status of the operation
    """

    print("apply wifi changes")
    try:
        output = subprocess.check_output(['/etc/init.d/network', 'restart'], stderr=subprocess.STDOUT)
        output = output.decode('utf-8')
        print(output)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def update_config_file(config_data):
    """
    Updates the config file with the new values
    
    Args:
        config_data (dict): A dictionary containing the new values to be written to the config file
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    for key, value in config_data.items():
        config.set('DEFAULT', key, value)
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    led_status_queue.append(("led_intensity", config_data['led_intensity']))
    print("Config file updated")

def check_config_values(config_data):
    """
    Checks if the values in the config file are valid and updates them if they are not

    Args:
        config_data (dict): A dictionary containing the new values to be written to the config file
        
    Returns:
        dict: A dictionary containing the new values to be written to the config file
    """ 
        
    required_keys = ['sampling_period', 'write_period', 'new_file_period', 'upload_period']
    for key in required_keys:
        if key not in config_data:
            return config_data
    sampling_period = int(config_data['sampling_period'])
    write_period = int(config_data['write_period'])
    new_file_period = int(config_data['new_file_period'])
    upload_period = int(config_data['upload_period'])
    if sampling_period < 1:
        config_data['sampling_period'] = str(1)
    if write_period < sampling_period:
        write_period = str(sampling_period * 2)
        config_data['write_period'] = write_period

    if new_file_period < write_period:
        new_file_period = str(write_period * 2)
        config_data['new_file_period'] = new_file_period
        
    if upload_period < new_file_period:
        upload_period = str(new_file_period * 2)
        config_data['upload_period'] = upload_period
    return config_data

# Receive the form data as JSON and print it
@app.route('/save_config', methods=['POST'])
def save_config():
    """
    Saves the new configuration to the config file and applies the changes
    
    Returns:
        JSON: A JSON object containing the status of the operation
    """
    message = ""
    try:
        config_data = request.get_json()
        print("Received JSON data:")
        print(config_data)
        config_data = check_config_values(config_data)
        print(config_data)
        update_config_file(config_data)
        # if google_drive.is_internet_available():
        #     if config_data['make_global'] == "true":
        #         google_drive.backup_config_file(parent_folder_id="root")
        #     google_drive.backup_config_file(parent_folder_name=DEVICE_ID)
        # else:
        #     message = "Internet is not available. Please connect to the internet and try again."
        # apply the changes
        if not stop_event.is_set():
            stop_event.set()
            time.sleep(5)
            stop_event.clear()
        
        return jsonify({"status": "success", "alert": message})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 400

@app.route('/reboot', methods=['POST'])
def reboot():
    """
    Reboots the device
    
    Returns:
        JSON: A JSON object containing the status of the operation
    """
    # run command reboot
    try:
        stop_event.set()
        time.sleep(2)
        
        # shutdown flask app
        shutdown_server()
            
              
        subprocess.run("reboot", shell=True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def shutdown_server():
    """
    Shuts down the flask app
    """
    # shutdown flask app
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if shutdown:
        shutdown()

if __name__ == "__main__":
    try:
        for file in os.listdir(TEMP_DIR):
            # try and read the file
            try:
                with open(os.path.join(TEMP_DIR, file), 'r') as f:
                    pass
                #move the file to the data directory
                new_file_name = os.path.join(DATA_DIR, os.path.join(file.split('_')[1]),file.split('_')[2], f"{file}.csv")
                os.rename(os.path.join(TEMP_DIR, file), new_file_name)
                print(f"File {file} moved to {new_file_name}")
            except:
                # if the file is not readable, delete it
                os.remove(os.path.join(TEMP_DIR, file))
        # #Delete content of the temp folder
        # subprocess.run(f"rm -rf {TEMP_DIR}/*", shell=True)
        # Create an empty queue
        led_status_queue = deque()
        led_status_queue.append(("settingUp", True))
        
        
        led_thread = threading.Thread(target=pulsate_led, args=(led_status_queue, status_queue,))  # red led loop
        led_thread.start()
        rtc = RTC.SDL_DS3231()

        # create and start threads
        data_thread = threading.Thread(target=read_write_loop, args=(rtc, led_status_queue, sensor_data_queue,))
        upload_thread = threading.Thread(target=upload_loop, args=(rtc, led_status_queue,))  # set RTC value and upload files to the internet
        internet_check_thread = threading.Thread(target=internet_check_loop, args=(led_status_queue,))  # check if the internet is available

        # Start all threads
        data_thread.start()
        upload_thread.start()
        internet_check_thread.start()

        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        if config.get('DEFAULT', 'STOPPED') == 'true':
            led_status_queue.append(("recording", False))
            stop_event.set()
        else:
            stop_event.clear()
            
        # Use Waitress to serve the Flask app
        # logging.getLogger('waitress.queue').setLevel(logging.ERROR)
        serve(app, host='0.0.0.0', port=5000)

        data_thread.join()
        upload_thread.join()
        internet_check_thread.join()
        led_thread.join()
    except Exception as e:  # other exceptions
        print(e)

