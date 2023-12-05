"""
File: HUB.py
Description: This script implements a PySide2 application for controlling a device and displaying sensor data.
Author: [Sami Kaab]
Date: [2023-07-03]
"""
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,QSplashScreen
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtCore import QCoreApplication, QThread, Qt
from PySide2.QtGui import QIcon, QPixmap
import sys
import paramiko
import time
import drive_ui
import dash_data_receive_server
import config_editor_ui
import authentification_ui

class DashAppThread(QThread):
    """ This class implements a thread for running the Dash app
    """
    def __init__(self, hostname=None):
        super().__init__()
        self.hostname = hostname
        self.sensorDataApp = None
    
    def run(self):
        """ This method runs the Dash app
        """
        self.sensorDataApp = dash_data_receive_server.SensorDataApp(self.hostname)
        self.sensorDataApp.run()
    
    def quit(self):
        """ This method quits the Dash app
        """
        if self.sensorDataApp.server: # Check if the server is running
            self.sensorDataApp.hostname = None
            self.sensorDataApp.server.shutdown()
            self.sensorDataApp.server.close()
        self.terminate() 
            
class MainWindow(QMainWindow):
    """ This class implements a PySide2 application for controlling a device and displaying sensor data.
    """
    def __init__(self):
        super().__init__()
        # Create and display the splash screen
        splash_image = QPixmap("images/standupdeskproject_logo.png")
        self.splash = QSplashScreen(splash_image, Qt.WindowStaysOnTopHint)
        self.splash.show()

        self.setWindowTitle("Be Up Standing - Not for comercial use, research purposes only")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('images/standup_logo.ico'))

        # Initialize variables
        self.file_explorer = None
        self.ssh_client = None
        self.hostname = None
        self.username = 'root'
        self.password = None
        
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)  # Main vertical layout
        
        self.web_view = QWebEngineView(self)
        self.web_view.load("http://127.0.0.1:8050/")
        self.web_view.setZoomFactor(0.8)
        layout.addWidget(self.web_view)
        
        button_layout = QHBoxLayout()  # Horizontal layout for buttons
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect)
        button_layout.addWidget(self.connect_button)
        
        open_config_editor_button = QPushButton("Configure", self)
        open_config_editor_button.clicked.connect(self.open_config_editor)
        button_layout.addWidget(open_config_editor_button)

        self.start_stop_button = QPushButton("Stop Recording", self, enabled=False)
        self.start_stop_button.clicked.connect(self.start_stop_program)
        button_layout.addWidget(self.start_stop_button)

        open_drive_button = QPushButton("Open Drive", self)
        open_drive_button.clicked.connect(self.open_drive)
        button_layout.addWidget(open_drive_button)

        layout.addLayout(button_layout)  # Add the button layout to the main layout
        
        # Create a thread for running the Dash app
        self.dashAppThread = DashAppThread()
        self.dashAppThread.start()
        
        self.splash.close()
                
        
    def closeEvent(self,event):
        """ This method is called when the window is closed
        """
        self.web_view.destroy()
        if self.dashAppThread.isRunning():
            self.dashAppThread.quit()
            self.dashAppThread.wait()
        event.accept()
        QCoreApplication.exit()  # Exit the application event loop

    def get_login(self):
        """ This method opens the login window
        """
        self.login_window = authentification_ui.LoginWindow()
        # Connect the closed signal to the set_login_info method
        self.login_window.closed.connect(lambda hostname, password, login_requested : self.set_login_info(hostname, password, login_requested))
        self.login_window.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.login_window.show()
    
    def set_login_info(self, hostname, password,login_requested):
        """ This method sets the login information
            Args:
                hostname (str): The hostname of the device
                password (str): The password of the device
                login_requested (bool): True if the user clicked the login button
        """
        if login_requested:
            self.hostname = hostname
            self.password = password
            self.dashAppThread.sensorDataApp.hostname = hostname
            self.connect()
        
    def connect(self):
        """ This method connects to the device via SSH
        """
        if self.hostname is None: # If the hostname is not set, open the login window
            self.get_login()
        else:
            if self.ssh_client is None: # If the SSH client is not set, connect to the device
                try:
                    
                    # Connect to the device via SSH
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh_client.connect(self.hostname, username=self.username, password=self.password)
                    self.ssh_client =  ssh_client
                    self.connect_button.setText("Disconnect")
                    self.start_stop_button.setDisabled(False)
                    self.is_device_running() # Check if the program is running on the device
                    QMessageBox.information(self, "Connection Successful", "Connected to device")

                except Exception as e:
                    self.ssh_client = None
                    self.hostname = None
                    self.password = None
                    QMessageBox.critical(self, "Connection Error", "Could not connect to device")
            else: # If the SSH client is set, disconnect from the device
                self.start_stop_button.setDisabled(True)
                self.connect_button.setText("Connect")
                self.ssh_client.close()    
                self.ssh_client = None
                self.hostname = None
                self.password = None
                QMessageBox.information(self, "Connection Closed", "Disconnected from device")

    def is_device_running(self):
        """ This method checks if the program is running on the device
        Returns:
            bool: True if the program is running on the device
        """
        if self.ssh_client is not None:
            try:
                # Execute the command to check if the program is running
                command = 'pgrep -f main'
                stdin, stdout, stderr = self.ssh_client.exec_command(command)

                # Read the output of the command
                output = stdout.read().decode().strip()

                # Check if the program is running
                if output:

                    self.start_stop_button.setText("Stop Recording")
                    return True
                else:
                    self.start_stop_button.setText("Start Recording")
                    return False

            except Exception as e:
                return False
        else:
            # add message box to say device is not connected
            QMessageBox.critical(self, "Error", "Device is not connected")

    def open_drive(self):
        """ This method opens the drive window
        """
        self.file_explorer = drive_ui.FileExplorer()
        self.file_explorer.show()
    
    def open_config_editor(self):
        """ This method opens the config editor window
        """
        if self.ssh_client is not None:
            self.config_editor = config_editor_ui.ConfigEditor(self.hostname, self.password)
            self.config_editor.setWindowFlags(Qt.WindowStaysOnTopHint)

            self.config_editor.show()
        else:
            QMessageBox.critical(self, "Connection Error", "Device is not connected")
        
    def check_device_stopped(self,i):
        """ This method checks if the device has stopped
            Args:
                i (int): The number of times the method has been called
        """
        if i > 30:
            command = 'kill $(pgrep -f main)'
            if self.ssh_client is not None:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
            command = 'kill -9 $(pgrep -f main)'
            if self.ssh_client is not None:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
        # Function to check if the device has stopped
        device_running = self.is_device_running()
        if device_running:
            # If the device is still running, check again after 1 second
            i+=1
            time.sleep(1) 
            self.check_device_stopped(i)
        else:
            # If the device has stopped, enable the start/stop button
            self.start_stop_button.setDisabled(False)

    def start_stop_program(self):
        """ This method starts or stops the program
        """
        device_running = self.is_device_running()
        if self.ssh_client is not None: # If the SSH client is set
            if device_running: # If the program is running on the device
                try:
                    self.start_stop_button.setDisabled(True)
                    # Execute the command to stop the program
                    command = 'kill $(pgrep -f main)'
                    stdin, stdout, stderr = self.ssh_client.exec_command(command)
                    time.sleep(1)
                    # Execute the command to stop the program
                    command = 'kill -9 $(pgrep -f main)'
                    stdin, stdout, stderr = self.ssh_client.exec_command(command)
                    for i in range(30):
                        time.sleep(1)
                        stillrunning = self.is_device_running()
                        if not stillrunning:
                            break
                    self.start_stop_button.setDisabled(False)
                    return False
                except Exception as e:
                    pass
            else: # If the program is not running on the device
                try:
                    # Execute the command to run the program
                    command = 'source /root/Firmware/shell_scripts/run_stand_up.sh'
                    stdin, stdout, stderr = self.ssh_client.exec_command(command)
                    self.start_stop_button.setDisabled(True)
                    QMessageBox.information(self, "Start up", "The device may take up to 30 seconds to start.")
                    for i in range(30):# wait 30 seconds for the device to start
                        time.sleep(1)
                        stillrunning = self.is_device_running()
                        if stillrunning:
                            break
                    self.start_stop_button.setDisabled(False)
                    return False
                except Exception as e:
                    pass
        else:
            # add message box to say device is not connected
            QMessageBox.about(self, "Conncetion Error", "Device is not connected")
                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
