# NOT IN USE

#!/bin/ash
source /root/Firmware/venv/bin/activate

output=$(python /root/Firmware/test_programs/rtc_test.py 2>&1)

# Check the output to determine if the sensor is working
if echo "$output" | grep -q "OK"; then
    echo "RTC test: passed"
else
    echo "RTC test: failed"
fi

output=$(python /root/Firmware/test_programs/hdp_test.py 2>&1)

# Check the output to determine if the sensor is working
if echo "$output" | grep -q "OK"; then
    echo "hdp test: passed"
else
    echo "hdp test: failed"
fi

output=$(python /root/Firmware/test_programs/laser_distance_test.py 2>&1)

# Check the output to determine if the sensor is working
if echo "$output" | grep -q "OK"; then
    echo "distance test: passed"
else
    echo "distance test: failed"
fi