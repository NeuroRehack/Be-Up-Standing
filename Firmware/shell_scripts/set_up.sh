# this script is used to set up the Omega2+ for the first time and install all the required packages

#!/bin/ash

# Check if script is running with root privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run with root privileges. Please use sudo or run as root."
  exit 1
fi

# Check internet connectivity
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
  echo "Internet is available. Proceeding with commands..."

  echo "Updating packages"
  opkg update || { echo "Failed to update packages."; exit 1; }

  echo "Installing required packages"
  opkg install python3 python3-pip pyOnionGpio || { echo "Failed to install packages."; exit 1; }

  echo "Setting up virtual environment"
  pip3 install virtualenv || { echo "Failed to install virtualenv."; exit 1; }
  virtualenv /root/Firmware/venv || { echo "Failed to create virtual environment."; exit 1; }
  source /root/Firmware/venv/bin/activate || { echo "Failed to activate virtual environment."; exit 1; }

  echo "Installing Python packages"
  mkdir /root/temp
  export TMPDIR=/root/temp
  pip install -r requirements.txt || { echo "Failed to install Python packages."; exit 1; }
  mv /root/Firmware/lib/flow.py /root/Firmware/venv/lib/python3.6/site-packages/google_auth_oauthlib/flow.py || { echo "Failed to move flow.py."; exit 1; }

  # # automatically run the stand_up script on boot
  # line_to_add="source /root/Firmware/shell_scripts/run_stand_up.sh &"
  # rc_local_file="/etc/rc.local"
  # # Check if the line already exists in rc.local
  # if grep -qF "$line_to_add" "$rc_local_file"; then
  #   echo "Line already exists in rc.local. No changes needed."
  # else
  #   # Add the line before 'exit 0' in rc.local
  #   sed -i "/^exit 0/i $line_to_add" "$rc_local_file" || { echo "Failed to add line to rc.local."; exit 1; }
  #   echo "Line added successfully to rc.local."
  # fi
  # automatically run the check_and_restart script every minute
  (crontab -l ; echo "* * * * * source /root/Firmware/shell_scripts/check_and_restart.sh") | crontab -
  echo "check_and_restart.sh added to crontab."

# rename /etc/rc.button/reset to /etc/rc.button/reset_copy and move /root/Firmware/shell_scripts/reset to /etc/rc.button/reset
  mv /etc/rc.button/reset /etc/rc.button/reset_copy || { echo "Failed to rename reset."; exit 1; }
  mv /root/Firmware/shell_scripts/reset /etc/rc.button/reset || { echo "Failed to move reset."; exit 1; }
  chmod +x /etc/rc.button/reset || { echo "Failed to change permissions for reset."; exit 1; }
  echo "reset script moved to /etc/rc.button/reset."

  echo "Setup complete. Please reboot the device to apply changes."

else
  echo "No internet connection found. Please check your internet connection."
fi