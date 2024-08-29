## [🏠 HOME](./README.md) | [🔧 Firmware](Firmware/README.md) | [💻 Software](Software/README.md) | [📊 Analysis](Analysis/README.md)
# Desk Positioning System 


This project aims to monitor the usage of a standing desk by measuring its height and detecting whether someone is present. The Desk Positioning System utilizes an Omega2 Pro SBC (Single-Board Computer) to read data from a human presence sensor and a distance sensor, storing this data localy. The data is periodically uploaded to Google Drive for easy remote access and analysis.

<p align="center">
  <img src="Documentation\StandUpDevice.png" width="400">
  <img src="Documentation\standup_device_assembly1.gif" width="400">
</p>

## Features
- **Desk Height Monitoring:** A laser distance sensor measures the distance between the desk and the floor, enabling the system to determine whether the desk is in a sitting or standing position.
- **Human Presence Detection:** An mmWave human presence detector identifies if a person is present and whether they are standing or sitting in front of the desk.
- **Data Logging:** Data from the sensors is processed and recorded by the Omega2 Pro, and timestamped using a real-time clock (RTC) module. The data is saved locally and periodically uploaded to Google Drive.
- **Power Management:** Powered by a rechargeable LiPo battery, the system remains operational during power outages.
- **Wi-Fi Connectivity:** The device uploads data to Google Drive when an internet connection is available. In case of network failure, data is stored locally for later upload.
- **Web Interface:** Each device hosts a unique web interface accessible via a specific URL, allowing users to:
  - Configure device settings (e.g., sampling frequency)
  - Start/stop data recording
  - Visualize recorded data in real-time
  - Manage Wi-Fi settings and monitor battery status
- **LED Indicator:** Provides visual feedback on operational status, such as internet connectivity and recording activity.
  

<p align="center">
  <img src="Documentation\Data_flow_diagram.png" width="800">
</p>

## Repo Overview
- **Firmware:** Contains the code running on the Omega2 Pro, responsible for data collection, processing, and cloud synchronization.
- **Software:** Includes scripts for downloading data from Google Drive
- **Analysis:** Provides instructions for analyzing the collected data to understand desk usage patterns.

## Getting Started
### Assembly and Setup

Follow the instructions in the [Firmware README](Firmware/README.md) to assemble the hardware and install the necessary firmware.

## Software

The scripts in software can be used to navigate, download and delete data from the google drive. For more information see the [Software README](Software/README.md).
## Data Analysis

The data collected by the Desk Positioning System can be analyzed to understand desk usage patterns. Detailed instructions for analyzing the data are available in the [Analysis README](Analysis/README.md).

## License

This project is licensed under the GNU General Public License. You may redistribute and/or modify it under the terms of the [GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html) (or any later version) as published by the Free Software Foundation.

For more details, see the [LICENSE](LICENSE) file.