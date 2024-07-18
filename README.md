This project aims to monitor the use of standing desk by measuring the height of the desk and whether someone is present or not.
This project utilises a Omega2 Pro to read data from a human presence sensor and a distance sensor and, store it in a CSV file. The data is periodically uploaded to Google Drive.

<p align="center">
  <img src="Documentation\CAD\StandUpDevice.png" width="400">
  <img src="Documentation\CAD\standup_device_assembly.gif" width="400">
</p>

# Required material
- [Omega2 Pro](https://onion.io/store/omega2-pro/)
- [DFRobot_mmWave module](https://www.dfrobot.com/product-2282.html)
- [PiicoDev_VL53L1X module](https://www.sparkfun.com/products/14722)
- [SDL_DS3231 module](https://www.jaycar.com.au/rtc-clock-module-for-raspberry-pi/p/XC9044?pos=1&queryId=f5734bdf10cb6c5024d07c37201f1d5b&sort=relevance&searchText=rtc)
- [LiPo battery 3.7V 1100mAh](https://core-electronics.com.au/polymer-lithium-ion-battery-1000mah-38458.html)
- Jumper wires
- USB A to micro USB cable

# Wiring schematic
<!--embed image center a resized with original ratio: Documentation/Wiring_Diagram.png-->
<p align="center">
  <img src="Documentation/Wiring_Diagram.png" width="400">
</p>

# Setting up the Omega2 Pro
The Omega2 Pro is a headless device, meaning that it does not have a screen or keyboard. In order to set it up you need to connect it to a computer using a micro USB cable and connect to it using a serial terminal.
The device requires internet access in order to install the necessary packages.

```sh
wifisetup add -ssid <ssid> -encr psk2 -password <password>
```

Replace ssid and password with the name and password of your wifi network.
You should now have internet access, which you can verify by pinging a website:

```sh
ping duckduckgo.com
```

We first need to install git and ca-bundle in order to be able to clone the repository:
```sh
opkg update && opkg install git git-http ca-bundle
```
We can now install the necessary Omega2 and python packages. Clone the Firmware folder in the repository from the root folder:
```sh
cd /root && git clone --depth 1 --filter=blob:none https://github.com/NeuroRehack/RADOM.git && mv ./RADOM/Firmware . && rm -r RADOM
```
then navigate to the Firmware folder and run the setup script:
```sh
cd /root/Firmware && source /root/Firmware/shell_scripts/set_up.sh
```
this script will install the necessary packages and set up the Omega2 to run the program on startup.  
Next run the omega_rename script:
```sh
source ./shell_scripts/omega_rename.sh
```
This script will amongst other things change the default wifi name and password of the omega as well as the device's password.  
The device should now be ready for use. Just restart it using ```reboot``` and it should start running the program on startup.

# Setting up a google drive API
The data recorded is uploaded to a google drive using the google drive api. For the program to use the api it is necessary to generate a credentials file.
You can find instructions on how to set up a google drive api [here](https://developers.google.com/drive/api/quickstart/python).  
Since we are using a headless device it is not possible for us to generate tokens which are necessary when using a normal google account and require a webbrowser based authentification which we cannot perform. For this reason make sure to link a google service account to the project.
Once you have generated the credentials file, copy it to the Firmware folder on the Omega2 Pro and rename it "credentials.json". You will also need it for accessing the google drive using the drive_cloner.py script from your computer.

# Software
There are two main scripts that are of use, the drive_cloner_ui.py script and and the drive_ui.py script. The drive_cloner_ui.py script is used to automatically clone the data from the google drive to your computer. After running it it the google drive should be empty and all the data locally stored in the chosen directory.  
The drive_ui.py script can be used to visualise the data in the google drive and allows the user to download or delete data