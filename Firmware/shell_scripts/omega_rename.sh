# this script is run on the omega to change the hostname and wifi name
#!/bin/ash

# Check if script is running with root privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run with root privileges. Please use sudo or run as root."
  exit 1
fi

old_name="Omega-"  # Specify the prefix of the old hostname
new_name="dps"  # Specify the new hostname prefix

# Find the line with the hostname and extract the ID
id=$(grep "option hostname" /etc/config/system | awk -F"'" '{print $2}' | awk -F"${old_name}" '{print $2}')

# Generate the new device ID
new_line="DEVICE_ID ='${id}'"

# Replace the old line with the new line in the shared resources file
sed -i "s|DEVICE_ID =.*|${new_line}|" /root/Firmware/shared_resources.py

echo "Set DEVICE_ID to ${id}"

# Generate the new hostname
new_line="option hostname '${new_name}-${id}'"

# Replace the old line with the new line in the system configuration file
sed -i "s|option hostname.*|${new_line}|" /etc/config/system

# Update the current hostname
echo "Hostname changed to ${new_name}-${id}"

# Find the line with the omega wifi name and extract the ID
id=$(grep "option ssid" /etc/config/wireless | awk -F"'" '{print $2}' | awk -F"${old_name}" '{print $2}')

# Generate the wifi name
new_line="option ssid '${new_name}-${id}'"

# Replace the old line with the new line in the wireless configuration file
sed -i "s|option ssid 'Omega-.*|${new_line}|" /etc/config/wireless

echo "Wifi name changed to ${new_name}-${id}"

# # # # ask for a new password for the omega's wifi
# # # pwd=""
# # # while [ ${#pwd} -le 7 ]; do
# # #     read -p "Enter a password (must be longer than 7 characters): " pwd
# # # done

# # # new_line="option key '${pwd}'"

# # # sed -i "/^config wifi-iface 'ap'$/,/^$/ s/option key '.*'/option key '$pwd'/" /etc/config/wireless

# # # echo "Wifi password changed"

# change the Omega root password
echo -e dps12345678\\ndps12345678 | passwd

# /etc/init.d/network restart