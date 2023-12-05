"""
File: authentification_ui.py
Description: This script implements a login window for authentication. It provides a graphical user interface (GUI) using PySide2 for users to enter their ID and password for the device 
Author: [Sami Kaab]
Date: [2023-07-03]
"""
from PySide2.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QMessageBox, QHBoxLayout, QCheckBox
from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
import sys
from helper_functions import get_wifi_name

"""
This class implements a login window for authentication. It provides a graphical user interface (GUI) using PySide2 for users to enter their ID and password for the device.
"""
class LoginWindow(QMainWindow):
    closed = Signal(str, str, bool)  # Add a signal to emit the hostname and password

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setWindowIcon(QIcon('images/standup_logo.ico'))

        self.setGeometry(100, 100, 300, 150)

        self.hostname = None
        self.password = None
        self.login_requested = False

        # Create widgets
        self.id_label = QLabel("ID:", self)
        self.id_input = QLineEdit(self)
        wifi_name = get_wifi_name()
        value = wifi_name if wifi_name is not None else value
        value = value.split("-")[1] if "-" in value else ''
        value = value.lower()
        
        self.id_input.setText(value)
        self.password_label = QLabel("Password:", self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.show_password_checkbox = QCheckBox("Show Password", self)
        self.login_button = QPushButton("Login", self)

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.id_label)
        layout.addWidget(self.id_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        
        # Add the show password checkbox and login button to a horizontal layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.show_password_checkbox)
        button_layout.addWidget(self.login_button)
        layout.addLayout(button_layout)

        # Create central widget and set the layout
        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Connect button click event to the login function
        self.login_button.clicked.connect(self.login)

        # Connect the checkbox state change event to the toggle_password_visibility function
        self.show_password_checkbox.stateChanged.connect(self.toggle_password_visibility)

    """
    This function is called when the login button is clicked. It checks if the ID and password are valid and emits the hostname and password if they are.
    """
    def login(self):
        user_id = self.id_input.text()
        password = self.password_input.text()

        if len(user_id) != 4:
            QMessageBox.warning(self, "Invalid ID", "Please enter a 4-character ID.\nThe ID should be the last four characters of the device WiFi network name.")
        elif len(password) < 1:
            QMessageBox.warning(self, "Invalid password", "Please enter your password.")
        else:
            self.hostname = f"standup-{user_id}.local"
            self.password = password
            self.login_requested = True
            self.close()

    """
    This function is called when the checkbox state is changed. It toggles the password visibility.
    """
    def toggle_password_visibility(self, state):
        if state == 2:  # Checkbox is checked
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

    """
    This function is called when the window is closed. It emits the hostname and password.
    """
    def closeEvent(self, event):
        self.destroy()
        self.closed.emit(self.hostname, self.password, self.login_requested)  # Emit the signal with the hostname and password
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
