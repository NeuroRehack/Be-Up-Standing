#!/bin/sh

# A shell script to check if a program is running and restart it if it's not.

PROGRAM_NAME="main_flask"

# Check if the program is running
if pgrep -f $PROGRAM_NAME > /dev/null; then
    # Get the PID of the program
    PID=$(pgrep -o -f $PROGRAM_NAME)

    # Get the CPU usage of the program
    CPU_USAGE=$(top -n 1 -b | grep "$PROGRAM_NAME" | head -n 1 | awk -F' ' '{print $7}' | tr -d '%')

    # Check if CPU usage is lower than 20
    if [ "$CPU_USAGE" -lt 20 ]; then
        echo "CPU usage of $PROGRAM_NAME is below 50%: $CPU_USAGE%"
        kill -9 $(pgrep -f $PROGRAM_NAME)
        source /root/Firmware/shell_scripts/run_stand_up.sh &  
    else
        echo "CPU usage of $PROGRAM_NAME is above or equal to 50%: $CPU_USAGE%"
    fi
else
    echo "$PROGRAM_NAME is not running."
    source /root/Firmware/shell_scripts/run_stand_up.sh &  

fi
