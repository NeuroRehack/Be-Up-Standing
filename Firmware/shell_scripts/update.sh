# NOT IN USE

# check for internet connection
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    kill -9 $(pgrep -f main)
    cd /root
    # clone repo without history and check if it worked
    git clone --depth 1 --filter=blob:none https://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@github.com/SamiKaab/Be-Up-Standing || 
        { 
        echo "Failed to clone repo."; 
        exit 1;
        }  
    # copy files from repo to Firmware folder
    cp -r /root/Be-Up-Standing/Firmware/* ./Firmware 
    rm -r /root/Be-Up-Standing
    echo "Activating virtual environment"
    source /root/Firmware/venv/bin/activate || { echo "Failed to activate virtual environment."; exit 1; }
    echo "Installing Python packages"
    export TMPDIR=/root/temp
    pip install -r /root/Firmware/requirements.txt || { echo "Failed to install Python packages."; exit 1; }
    source /root/Firmware/shell_scripts/omega_rename.sh
else
  echo "No internet connection found. Please check your internet connection."
fi