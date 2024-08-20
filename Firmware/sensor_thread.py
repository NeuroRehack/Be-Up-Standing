
import time
import os
from datetime import datetime, timedelta
import csv
import configparser
import lib.human_presence as human_presence
from lib.PiicoDev_VL53L1X import PiicoDev_VL53L1X
import lib.battery as battery
from shared_resources import FILE_HEADER, DATA_DIR, CONFIG_FILE, DEVICE_ID, TEMP_DIR, stop_event, lock, device_should_record, LOG_FILE,ROOT_DIR
import logging

def write_data_to_file(fileName, data):
    """
    Write the data to a CSV file with the given file name.

    If the file already exists, the data will be appended to it.

    Args:
        fileName (str): The name of the file to write to.
        data (list): A list of data to write to the file.
    """
    # for folders in filename, create them if they don't exist  
    path = "/"
    fileName = os.path.normpath(fileName)
    for folder in fileName.split(os.path.sep)[:-1]:
        path = os.path.join(path, folder)
        if not os.path.exists(path):
            os.mkdir(path)
            
    mode = 'a' if os.path.exists(fileName) else 'w'
    with open(fileName, mode, newline='') as f:
        # Create a CSV writer object
        writer = csv.writer(f)

        # Write the data to the CSV file
        writer.writerows(data)

def create_folders(fileName):
    """
    Create folders in the given file path if they don't exist.

    Args:
        fileName (str): The file path to create folders in.
    """
    path = "/"
    fileName = os.path.normpath(fileName)
    for folder in fileName.split(os.path.sep)[:-1]:
        path = os.path.join(path, folder)
        if not os.path.exists(path):
            os.mkdir(path)

def read_write_loop(rtc, status_queue, sensor_data_queue):
    """
    Continuously read sensor data and write it to a CSV file.

    This function reads sensor data from the human presence sensor and distance sensor, and stores
    it in a list. The data is then written to a CSV file with the specified file name every `WRITE_PERIOD`
    seconds.
    """
    # logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format='%(asctime)s %(message)s')
    # logging.info("sensor_thread: starting read_write_loop")

    with lock:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        SAMPLING_PERIOD = config.getint('DEFAULT', 'SAMPLING_PERIOD')
        WRITE_PERIOD = config.getint('DEFAULT', 'WRITE_PERIOD')
        NEW_FILE_PERIOD = config.getint('DEFAULT', 'NEW_FILE_PERIOD')
        UPLOAD_PERIOD = config.getint('DEFAULT', 'UPLOAD_PERIOD')
        ID = config.get('DEFAULT', 'ID')
        WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
        SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
    
    # init sensors
    #print("setting up HDP sensor")
    human_presence.init_hdp()
    #print("setting up Distance sensor")
    distSensor = PiicoDev_VL53L1X() 
   

    # Initialize the list of data with the header
    data = [FILE_HEADER]
    # Compute the file name
    lastWriteTime = rtc.read_datetime()
    lastNewFileTime = lastWriteTime
    date = lastNewFileTime.strftime("%y%m%d")
    formattedDatetime = lastNewFileTime.strftime("%y%m%d_%H%M%S")
    fileName = os.path.join(ROOT_DIR,TEMP_DIR,f"{DEVICE_ID}_{ID}_{formattedDatetime}")  
    
    status_queue.append(("settingUp", False))
    
    stop = False
    last_sample = rtc.read_datetime()
    # Continuously read sensor data and write it to a CSV file
    while True:
        if stop_event.is_set() and not stop: # the stop event has been set and we need to stop recording
            stop = True
            # close the current file
            write_data_to_file(fileName, data)
            data = [FILE_HEADER]
            lastWriteTime = rtc.read_datetime()
            # move the file from the temp folder to the data folder and rename it
            newFilePath = os.path.join(ROOT_DIR,DATA_DIR,ID,date,f"{DEVICE_ID}_{ID}_{formattedDatetime}.csv")
            create_folders(newFilePath)
            os.rename(fileName,f"{newFilePath}")
            # logging.info("sensor_thread: stop event set, stopping recording")

            
        elif stop and not stop_event.is_set(): # the stop event has been cleared and we need to start recording again
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            SAMPLING_PERIOD = config.getint('DEFAULT', 'SAMPLING_PERIOD')
            WRITE_PERIOD = config.getint('DEFAULT', 'WRITE_PERIOD')
            NEW_FILE_PERIOD = config.getint('DEFAULT', 'NEW_FILE_PERIOD')
            ID = config.get('DEFAULT', 'ID')
            WAKE_AT = config.get('DEFAULT', 'WAKE_AT')
            SLEEP_AT = config.get('DEFAULT', 'SLEEP_AT')
            print("sensor_thread: stop event cleared, starting recording again")
            # create a new file
            now = rtc.read_datetime()
            date = now.strftime("%y%m%d")
            formattedDatetime = lastNewFileTime.strftime("%y%m%d_%H%M%S")
            fileName = os.path.join(ROOT_DIR,TEMP_DIR,f"{DEVICE_ID}_{ID}_{formattedDatetime}")  
            lastNewFileTime = now
            stop = False
            # logging.info("sensor_thread: stop event cleared, starting recording again")
    
        if device_should_record(WAKE_AT, SLEEP_AT, rtc) and not stop: # the device should be recording and the stop event has not been set

            status_queue.append(("recording", True))

            # Read data from sensors
            with lock:
                now = rtc.read_datetime()
                last_sample = now
            hp = human_presence.read_presence()
            distance = distSensor.read()
            battery_level = round(battery.compute_battery_level(),2)
            # Append data to the list
            line = [now, distance, hp]
            data.append(line)
            graph_data = [now, distance, hp, battery_level]
            sensor_data_queue.append(graph_data)

            # print("{now} {distance} {hp}".format(distance=distance, hp=hp, now=now))

            elapsed = now - lastNewFileTime
            if elapsed > timedelta(seconds=NEW_FILE_PERIOD): # create a new file
                # logging.info("sensor_thread: creating new file")
                # closed the last file
                write_data_to_file(fileName, data)
                data = [FILE_HEADER]
                lastWriteTime = now
                newFilePath = os.path.join(ROOT_DIR,DATA_DIR,ID,date,f"{DEVICE_ID}_{ID}_{formattedDatetime}.csv")
                create_folders(newFilePath)
                os.rename(fileName,f"{newFilePath}")
                
                # get new file name
                date = now.strftime("%y%m%d")
                formattedDatetime = lastNewFileTime.strftime("%y%m%d_%H%M%S")
                fileName = os.path.join(ROOT_DIR,TEMP_DIR,f"{DEVICE_ID}_{ID}_{formattedDatetime}")  
                lastNewFileTime = now
                
            # Write data to CSV file after set amount of time has elapsed
            elapsed = now - lastWriteTime
            if elapsed > timedelta(seconds=WRITE_PERIOD):
                # logging.info("sensor_thread: writing data to file")
                write_data_to_file(fileName, data)
                # Reset data and time for the next write interval
                data = []
                lastWriteTime = now

            # Wait for the specified sampling period before collecting more data
            sleepFor = SAMPLING_PERIOD - (rtc.read_datetime() - last_sample).total_seconds()
            time.sleep(sleepFor if sleepFor > 0 else 0 )
        else:
            status_queue.append(("recording", False))
            #print(f"recording will wake in {seconds_until_wake()}")
            sleepFor = SAMPLING_PERIOD - (rtc.read_datetime() - last_sample).total_seconds()
            time.sleep(sleepFor if sleepFor > 0 else SAMPLING_PERIOD )
            
    recording = False
    status_queue.append(("recording", recording))
    print("read_write_loop exiting")
    # logging.info("read_write_loop exiting")