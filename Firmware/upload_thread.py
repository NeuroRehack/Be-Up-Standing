import requests
from datetime import datetime, timedelta
import os
import time
import configparser
import backup_to_drive as google_drive
from shared_resources import FILE_HEADER, ROOT_DIR, DATA_DIR, TEMP_DIR, CONFIG_FILE,stop_event, lock, device_should_record,LOG_FILE,DEVICE_ID
import subprocess
import logging

def get_time_from_internet():
    """
    Retrieve the current date and time from the internet using the worldtimeapi.org API.

    Returns:
        A datetime object representing the current date and time.
    """
    # Define the URL of the API and specify the timezone to retrieve the time for
    url = 'http://worldtimeapi.org/api/timezone/Australia/Brisbane'  # or any other timezone you want to get the time for

    # Send a GET request to the API and retrieve the response data
    response = requests.get(url)
    data = response.json()

    # Extract the datetime string from the response data and convert it to a datetime object
    datetime_str = data['datetime'].split("+")[0]
    dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f")
    


    # Return the datetime object
    return dt

def upload_loop(rtc, status_queue):
    """
    Periodically upload the sensor data to Google Drive.

    This function checks for an internet connection and, if available, updates the real-time clock (RTC)
    module with the current time from the internet. It then backs up the sensor data to Google Drive.
    The status of the backup process is indicated using the red LED.

    Returns:
        None.
    """
    
    # set up logging
    # logging.basicConfig(filename= LOG_FILE , level=logging.DEBUG, format='%(asctime)s %(message)s')
    # logging.info('upload thread: started')
  
    # logging.getLogger("requests").setLevel(logging.WARNING)
    # logging.getLogger("urllib3").setLevel(logging.WARNING)
    # logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    # logging.getLogger("oauth2client").setLevel(logging.WARNING)
    # logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
    # logging.getLogger("googleapiclient.http").setLevel(logging.WARNING)
    # logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
    # logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
    
    with lock:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        UPLOAD_PERIOD = config.getint('DEFAULT', 'UPLOAD_PERIOD')
        WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
        SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
        ID = config.get('DEFAULT', 'ID')
        # ONLINE_CONFIG = config.get('DEFAULT', 'ONLINE_CONFIG')
    

    # Update RTC with the current time if internet connection is available and upload config file to google drive
    if google_drive.is_internet_available():
        dt = get_time_from_internet()
        rtc.write_datetime(dt)
        # the commented out code below is for updating the config file from google drive
        # # print(f"Use global config file: {ONLINE_CONFIG}")
        # # if ONLINE_CONFIG == "true": # if online config is true, download config from google drive
        # #     print("downloading config")
        # #     google_drive.download_file(service = None, parent_folder_id = 'root' , file_name = CONFIG_FILE, destination = TEMP_DIR)
            
        # #     new_config = configparser.ConfigParser()
        # #     new_config.read(os.path.join(TEMP_DIR, CONFIG_FILE))
        # #     # change password
        # #     password = new_config.get('DEFAULT', 'PASSWORD')
        # #     line  = f"echo -e \"{password}\\n{password}\" | passwd"
        # #     subprocess.run(line, shell=True)
        # #     excluded_keys = ['STOPPED', 'LED_INTENSITY']
        # #     for key in excluded_keys:
        # #         value = config.get('DEFAULT', key)
        # #         new_config.set('DEFAULT', key, value)
        # #     with open(CONFIG_FILE, 'w') as f:
        # #         new_config.write(f)
                
        # # # upload config file to google drive folder of device
        # # google_drive.backup_config_file(parent_folder_name=DEVICE_ID)
        

    # Continuously check for an internet connection and backup data to Google Drive
    last_upload_try = datetime.now()
    stop = False
    while True:
        if stop_event.is_set():
            stop = True
        elif stop:
            stop = False
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            UPLOAD_PERIOD = config.getint('DEFAULT', 'UPLOAD_PERIOD')
            WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
            SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
            ID = config.get('DEFAULT', 'ID')
            # the commented out code below is for updating the config file from google drive
            # # ONLINE_CONFIG = config.get('DEFAULT', 'ONLINE_CONFIG')
            # # print(f"Use global config file: {ONLINE_CONFIG}")
            # # if ONLINE_CONFIG == "true": # if online config is true, download config from google drive
            # #     print("downloading config")
            # #     google_drive.download_file(service = None, parent_folder_id = 'root' , file_name = CONFIG_FILE, destination = TEMP_DIR)
            # #     logging.info('upload thread: config file fetched from google drive')
                
            # #     new_config = configparser.ConfigParser()
            # #     new_config.read(os.path.join(TEMP_DIR, CONFIG_FILE))
            # #     # change password
            # #     password = new_config.get('DEFAULT', 'PASSWORD')
            # #     line  = f"echo -e \"{password}\\n{password}\" | passwd"
            # #     subprocess.run(line, shell=True)
            # #     excluded_keys = ['STOPPED', 'LED_INTENSITY']
            # #     for key in excluded_keys:
            # #         value = config.get('DEFAULT', key)
            # #         new_config.set('DEFAULT', key, value)
            # #     with open(CONFIG_FILE, 'w') as f:
            # #         new_config.write(f)
            # #     # upload config file to google drive folder of device
            # #     google_drive.backup_config_file(parent_folder_name=DEVICE_ID)
            # #     logging.info('upload thread: config file uploaded to google drive')
            
        if (rtc.read_datetime() - last_upload_try).total_seconds() > UPLOAD_PERIOD:
            last_upload_try = rtc.read_datetime()
            internet = google_drive.is_internet_available()
            if internet:
                dt = get_time_from_internet()
                rtc.write_datetime(dt)
        
                status_queue.append(("uploading", True))
                # Back up data to Google Drive and turn off the red LED to indicate success
                # file_list = [file for file in os.listdir(DATA_DIR) if file.endswith(".csv")]
                # logging.info('upload thread: starting to upload data')    
                try:
                    google_drive.upload(DEVICE_ID)
                except Exception as e:
                    print(f"problem encountered while uploading:\n{e}") 
                    # logging.info(f'upload thread: problem encountered while uploading:\n{e}')       
                # logging.info('upload thread: data uploaded')    
                status_queue.append(("uploading", False))

            else:
                status_queue.append(("uploading", False))
    
