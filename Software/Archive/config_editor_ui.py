"""
File: config_editor_ui.py
Description: A graphical user interface (GUI) using PySide2. It allows users to configure device parameters and send the configuration to a device. The GUI displays input fields for modifying settings such as sampling period, write period, and ID.
Author: [Sami Kaab]
Date: [2023-07-03]
"""

import configparser

import paramiko
from PySide2.QtCore import QTime
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QTimeEdit,
    QWidget,
    QMessageBox,
    QFileDialog,
)
from PySide2.QtGui import QIcon
from helper_functions import get_wifi_name
import os
import shutil
import json
import sys

"""
This class implements a configuration window for configuring device parameters. It provides a graphical user interface (GUI) using PySide2 for users to enter their ID and password for the device.
"""
class ConfigEditor(QMainWindow):
    DEFAULT_VALUES = {
        "Sampling Period (s)": "5",
        "Write Period (s)": "30",
        "New File Period (s)": "120",
        "Upload Period (s)": "120",
        "ID": "xxxx",
        "Wake At": "07:30",
        "Sleep At": "17:30",
    }

    LABEL_TO_CONFIG_VAR = {
        "Sampling Period (s)": "SAMPLING_PERIOD",
        "Write Period (s)": "WRITE_PERIOD",
        "New File Period (s)": "NEW_FILE_PERIOD",
        "Upload Period (s)": "UPLOAD_PERIOD",
        "ID": "ID",
        "Wake At": "WAKE_AT",
        "Sleep At": "SLEEP_AT",
    }

    def __init__(self, hostname=None, password=None):
        super().__init__()
        self.setWindowTitle("Configure")
        self.setWindowIcon(QIcon('images/standup_logo.ico'))
        
        # Initialize variables
        self.hostname = hostname
        self.username = 'root'
        self.password = password
        self.credentials_file = None

        # Create widgets
        self.config = configparser.ConfigParser()
        self.values = self.DEFAULT_VALUES.copy()

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QFormLayout(self.central_widget)

        self.labels = []
        self.widgets = []

        self.load_config()
        self.create_config_fields()
        
        self.select_file_button = QPushButton("Select Credentials File")
        self.select_file_button.clicked.connect(self.select_json_file)
        self.layout.addRow("", self.select_file_button)

        self.save_button = QPushButton("Save Config")
        self.save_button.clicked.connect(self.save_config)
        self.layout.addRow("", self.save_button)

    
    """
    Loads the configuration from the config.ini file.
    """
    def load_config(self):
        self.config.read("config.ini")
        if "DEFAULT" in self.config:
            for key in self.values:
                config_key = self.LABEL_TO_CONFIG_VAR[key]
                if config_key in self.config["DEFAULT"]:
                    self.values[key] = self.config["DEFAULT"][config_key]

    def load_config_from_values(self):
        """
        Loads the configuration from the values dictionary.
        """
        for key, value in self.values.items():
            for label in self.labels:
                if label.text() == key:
                    index = self.labels.index(label)
                    widget = self.widgets[index]
                    if isinstance(widget, QLineEdit):
                        cursor_position = widget.cursorPosition()
                        widget.setText(value)
                        widget.setCursorPosition(cursor_position)

                    elif isinstance(widget, QTimeEdit):
                        widget.setTime(QTime.fromString(value, "HH:mm"))

    def create_config_fields(self):
        """
        Creates the configuration fields for the GUI.
        """
        for key, value in self.values.items():
            label = QLabel(key, self)

            if key in ["Wake At", "Sleep At"]:
                time_edit = QTimeEdit(self)
                time_edit.setDisplayFormat("HH:mm")
                time_edit.setTime(QTime.fromString(value, "HH:mm"))
                time_edit.timeChanged.connect(self.update_value)

                self.widgets.append(time_edit)
                self.layout.addRow(label, time_edit)
            else:
                if key == "ID":
                    wifi_name = get_wifi_name()
                    og_value = value
                    value = wifi_name if wifi_name is not None else value
                    value = value.split("-")[1] if "-" in value else og_value
                    value = value.lower()

                self.values[key] = value
                line_edit = QLineEdit(value, self)
                line_edit.textChanged.connect(self.update_value)
                line_edit.editingFinished.connect(self.check_values)
                self.widgets.append(line_edit)
                self.layout.addRow(label, line_edit)

            self.labels.append(label)

    """
    Updates the value of a configuration field in the GUI.

    Args:
        value (str): The new value entered in the input widget.

    Returns:
        None
    """
    def update_value(self, value):
            
        sender = self.sender()
        index = self.widgets.index(sender)
        label = self.labels[index].text()
        new_value = self.check_value(label, value)
        value = new_value if new_value is not None else self.values[label]
        self.values[label] = value
        self.save_button.setText("Save Config")
        self.save_button.clicked.disconnect()
        self.save_button.clicked.connect(self.save_config)
        self.load_config_from_values()

    """
    Checks the validity of the configuration values and corrects them if necessary.

    Args:
        None

    Returns:
        None
    """
    def check_values(self):
        sampling_period = int(self.values["Sampling Period (s)"]) if self.values["Sampling Period (s)"] else 1
        write_period = int(self.values["Write Period (s)"]) if self.values["Write Period (s)"] else 1
        new_file_period = int(self.values["New File Period (s)"]) if self.values["New File Period (s)"] else 1
        upload_period = int(self.values["Upload Period (s)"]) if self.values["Upload Period (s)"] else 1
        error_found = False
        if write_period < sampling_period:
            write_period = sampling_period * 2
            error_found = True

        if new_file_period < write_period:
            new_file_period = write_period * 2
            error_found = True

        if upload_period < new_file_period:
            upload_period = new_file_period * 2
            error_found = True

        self.values["Sampling Period (s)"] = str(sampling_period)
        self.values["Write Period (s)"] = str(write_period)
        self.values["New File Period (s)"] = str(new_file_period)
        self.values["Upload Period (s)"] = str(upload_period)
        if error_found:
            QMessageBox.information(
                self,
                "Config Editor",
                "Invalid values have been corrected\n\nUpload Period (s) >= New File Period (s) >= Write Period (s) >= Sampling Period (s)",
            )
        self.load_config_from_values()

    """
    Checks the validity of a configuration value for a specific label.

    Args:
        label (str): The label associated with the configuration field.
        value (str): The value to be checked.

    Returns:
        str: The corrected value if it is valid, or None if it is invalid.
    """
    @staticmethod
    def check_value(label, value):
        if label in ("Sampling Period (s)", "Write Period (s)", "New File Period (s)", "Upload Period (s)"):
            if value != "":
                try:
                    v = int(value)
                    if v < 1:
                        value = "1"
                except ValueError:
                    value = None

        return value

    """
    Saves the configuration values to the config.ini file.

    Args:
        None

    Returns:
        None
    """
    def save_config(self):
        for key, value in self.values.items():
            config_key = self.LABEL_TO_CONFIG_VAR[key]
            if isinstance(value, QTime):
                value = value.toString("HH:mm")
            self.config["DEFAULT"][config_key] = value

        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

        self.save_button.setText("Send Config")
        self.save_button.clicked.disconnect()
        self.save_button.clicked.connect(self.send_config)

        self.statusBar().showMessage("Config saved successfully!")

    """
    Opens a file dialog to select a JSON credentials file.

    Args:
        None

    Returns:
        None
    """
    def select_json_file(self):
        file_dialog = QFileDialog()
        self.credentials_file, _ = file_dialog.getOpenFileName(self, "Select credentials File", "", "JSON Files (*.json)")
        if self.credentials_file is not None and not self.is_service_account_credentials(self.credentials_file):
            QMessageBox.information(self, "Config Editor", "Invalid JSON file selected\nMake sure that the file is a valid service account credentials file")
            self.credentials_file = None
        
    """
    Checks if a JSON file is a valid service account credentials file.

    Args:
        json_file_path (str): The path of the JSON file.

    Returns:
        bool: True if the JSON file is a valid service account credentials file, False otherwise.
    """
    def is_service_account_credentials(self, json_file_path):
        try:
            with open(json_file_path) as file:
                credentials = json.load(file)
                if (
                    credentials.get("type") == "service_account"
                    and "project_id" in credentials
                    and "client_email" in credentials
                    and "private_key" in credentials
                ):
                    return True
        except (IOError, ValueError):
            return False
        return False

    """
    Sends the configuration file and credentials file (if selected) to the device.

    Args:
        None

    Returns:
        None
    """
    def send_config(self):
        src = 'config.ini'
        dst = '/root/Firmware/config.ini'
        credentials_file_dst = '/root/Firmware/credentials.json'
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            with paramiko.Transport(self.hostname, 22) as t:
                t.connect(username=self.username, password=self.password)
                sftp = paramiko.SFTPClient.from_transport(t)
                sftp.put(src, dst)
                #check if a credentials file was selected
                if self.credentials_file is not None:
                    sftp.put(self.credentials_file, credentials_file_dst)
                    shutil.copy(self.credentials_file, os.path.join(os.getcwd(), "credentials.json"))
                sftp.close()
            self.statusBar().showMessage("Config sent successfully!")
            QMessageBox.information(self, "Config Editor", "Config sent successfully!")
            self.close()
        except paramiko.AuthenticationException:
            self.statusBar().showMessage("Authentication failed.")
        except paramiko.SSHException as e:
            self.statusBar().showMessage("SSH connection failed: " + str(e))
        except Exception as e:
            self.statusBar().showMessage("An error occurred: " + str(e))
        finally:
            client.close()

if __name__ == "__main__":
    app = QApplication([])
    window = ConfigEditor()
    window.show()
    sys.exit(app.exec_())
