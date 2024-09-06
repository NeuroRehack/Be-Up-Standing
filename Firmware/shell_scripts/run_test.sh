#!/bin/ash
source /root/Firmware/venv/bin/activate

cp /root/Firmware/test_programs/rtc_test.py /root/Firmware/test.py
python -u /root/Firmware/test.py 2>&1 | while IFS= read -r line; do
    echo "$line"
    # Append the line to a variable for checking after completion
    output="$output$line"$'\n'
done

# Check the output to determine if the sensor is working
if echo "$output" | grep -q "OK"; then
    echo "RTC test: passed"
else
    echo "RTC test: failed"
fi

cp /root/Firmware/test_programs/hdp_test.py /root/Firmware/test.py
python -u /root/Firmware/test.py 2>&1 | while IFS= read -r line; do
    echo "$line"
    # Append the line to a variable for checking after completion
    output="$output$line"$'\n'
done

# Check the output to determine if the sensor is working
if echo "$output" | grep -q "OK"; then
    echo "HDP test: passed"
else
    echo "HDP test: failed"
fi

cp /root/Firmware/test_programs/laser_distance_test.py /root/Firmware/test.py
python -u /root/Firmware/test.py 2>&1 | while IFS= read -r line; do
    echo "$line"
    # Append the line to a variable for checking after completion
    output="$output$line"$'\n'
done

# Check the output to determine if the sensor is working
if echo "$output" | grep -q "OK"; then
    echo "Laser distance test: passed"
else
    echo "Laser distance test: failed"
fi
rm /root/Firmware/test.py