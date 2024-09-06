<!-- add a link to go back to main readme file -->
## [🏠 HOME](../README.md) | [🔧 Firmware](./README.md) | [💻 Software](../Software/README.md) | [📊 Analysis](../Analysis/README.md)

## Required material
- [Omega2 Pro](https://onion.io/store/omega2-pro/)
- [DFRobot_mmWave module](https://www.dfrobot.com/product-2282.html)
- [PiicoDev_VL53L1X module](https://www.sparkfun.com/products/14722)
- [SDL_DS3231 module](https://www.jaycar.com.au/rtc-clock-module-for-raspberry-pi/p/XC9044?pos=1&queryId=f5734bdf10cb6c5024d07c37201f1d5b&sort=relevance&searchText=rtc)
- [LiPo battery 3.7V 1100mAh](https://core-electronics.com.au/polymer-lithium-ion-battery-1000mah-38458.html)
- 5 x Male to Female Jumper wires
- 2 x Male to QWIIC Jumper wires (4-pin)
- USB A to micro USB cable
- M3 Nylon 16mm screws and nuts

## Required equipment
- 3D printer
- Soldering iron
- Hot glue gun (optional)
- Computer
- Internet connection

## Required skills and experience
- 3d printing
- Soldering
- SSH and serial terminal
- Basic knowledge of linux navigation and commands

## Hardware setup 
### Wiring (~15 min)
Once you have all the necessary components, you can start assembling the hardware. The wiring schematic below shows how to connect the various components to the Omega2 Pro. 
This step may require you to solder pins onto some of the sensors. Wiring should take around 10-15 minutes.

<p align="center">
  <img src="../Documentation/Wiring_Diagram.png" width="390">
  <img src="../Documentation/DPS_mechanical_drawing.png" width="670">
  <img src="../Documentation/DPS_frame_mechanical_drawing.png" width="670">
</p>

### 3D printing the case (~3 hours)

You will need to 3d print a case to house the components and the frame to attach the device to the desk. The STL files can be found in the [CAD folder](../Documentation/CAD/). Make sure to print one of each of the following files:
- [Case Bottom](../Documentation/CAD/case_bottom.obj)
- [Case Top](../Documentation/CAD/case_top.obj)
- [Frame](../Documentation/CAD/frame.obj)
- [Clamping Part](../Documentation/CAD/clamping_part.obj)

On a printer with 0.2mm layer height, supports (64° overhang threshold), 10% infill, 250mm/s, it should take around 3 hours to print all the parts.

## Setting up a google drive API (~10 min)
The data recorded is uploaded to a google drive using the google drive api. For the program to use the api it is necessary to generate a credentials file.
You can find instructions on how to set up a google drive api [here](https://developers.google.com/drive/api/quickstart/python).  
Since we are using a headless device it is not possible for us to generate tokens which are necessary when using a normal google account and require a webbrowser based authentification which we cannot perform. For this reason make sure to link a google service account to the project.

You will have to copy the credentials to the Firmware folder on the Omega2 Pro and rename it "credentials.json". This will be done in the next section. 

You will also need it for accessing the google drive using the scripts in the Software folder (see the [Software README](../Software/README.md)).

## Setting up the Omega2 Pro (~30 min)
The Omega2 Pro is a headless device, meaning that it cannot be accessed using a graphical user interface. In order to set it up you need to plug it to a computer using a micro USB cable and connect to it using a serial terminal (e.g. Putty). The device requires internet access in order to install the necessary packages. This section should take around 30 minutes to complete depending on the internet connection.

- Once you have connected to the device using a serial terminal, you can set up the wifi using the following command:
  ```sh
  wifisetup add -ssid <ssid> -encr psk2 -password <password>
  ```
  Replace ssid and password with the name and password of your wifi network.

- Copy the credentials file to the Firmware folder on the Omega2 Pro.
  You can do this using scp:
  ```sh
  scp /path/to/credentials.json root@Omega-XXXX.local:/root/Firmware/credentials.json
  ```
  where /path/to/credentials.json is the path to the credentials file on your computer and `XXXX` is the last four digits of the Omega2 Pro ID.
- You should now have internet access, which you can verify by pinging a website:

  ```sh
  ping duckduckgo.com
  ```

  - We first need to install git and ca-bundle in order to be able to clone the repository:
  ```sh
  opkg update && opkg install git git-http ca-bundle
  ```
- We can now install the necessary Omega2 and python packages.

  - Download the source code from the latest release of the repository to your computer. Extract the files and copy the Firmware folder to the root of the Omega2 Pro. You can do this using scp:
  ```sh
  scp -r /path/to/Firmware root@Omega-XXXX.local:/root/
  ``` 
  where /path/to/Firmware is the path to the Firmware folder on your computer and `XXXX` is the last four digits of the Omega2 Pro ID.
  
  **NOTE**: You will need to have the Omega2 Pro connected to the same network as your computer.

  - **Alternatively**, you can clone the repository directly on the Omega2 Pro using git:

  ```sh
  cd /root && git init && git config core.sparseCheckout true && echo Firmware/ >> .git/info/sparse-checkout 
  ```
  ```sh
  git remote add origin https://github.com/NeuroRehack/Desk-Positioning-System.git && git pull origin master
  ```

- then navigate to the Firmware folder and run the setup script which will install the necessary packages and set up the Omega2 to run the program on startup.
  ```sh
  cd /root/Firmware && source /root/Firmware/shell_scripts/set_up.sh
  ```
  depending on the internet connection the setup might take a while. Once it is done you will need to reboot the device using ```reboot```.

- It is a good idea now to check that the sensors have been wired and are working correctly. You can do this by running the test script:
  ```sh
   source /root/Firmware/shell_scripts/run_test.sh 
  ```

- Next run the omega_rename script:
  ```sh
  source ./shell_scripts/omega_rename.sh
  ```
  This script will amongst other things change the default wifi name and password of the omega as well as the device's password.

The device should now be ready for use. Just restart it using ```reboot``` and it should start running the program on startup.

