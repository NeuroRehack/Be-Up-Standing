import threading
from datetime import datetime
# Lock for synchronization
lock = threading.Lock()

connected = False
uploading = False
recording = False
settingUp = True
# Create a flag to indicate if the threads should continue stop_event
stop_event = threading.Event()
ROOT_DIR = "/root/Firmware"
TEMP_DIR = "temp"
DATA_DIR = "data"
FILE_HEADER = ["Date time", "Distance(mm)", "Human Present"]
CONFIG_FILE = "config.ini"
LOG_FILE = "/root/Firmware/logs/standup.log"
DEVICE_ID ='A17E' # this is the device ID of the device !- hardcoded for now

def device_should_record(WAKE_AT, SLEEP_AT, rtc):
    """
    This function checks if the device should record data based on the current time and the wake up and sleep times.
    
    Args:
        WAKE_AT (str): The time at which the device should start recording data.
        SLEEP_AT (str): The time at which the device should stop recording data.
        rtc (PiicoDev_RTC): The real time clock object.
        
    Returns:
        bool: True if the device should record data, False otherwise.
    """
    current_time = rtc.read_datetime().time()
    start = datetime.strptime(WAKE_AT, "%H:%M").time()
    end = datetime.strptime(SLEEP_AT, "%H:%M").time()

    if start <= end:
        return start <= current_time <= end
    else:
        return start <= current_time or current_time <= end  
    
