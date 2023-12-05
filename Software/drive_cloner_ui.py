import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import hashlib
from tqdm import tqdm

import configparser
from tkinter import messagebox,filedialog
from tkinter import Tk
from datetime import datetime, timedelta
import requests

CONFIG_FILE = "drive_settings.ini"
SERVICE_ACCOUNT_CREDENTIALS = 'credentials.json'

def internet_available():
    """Check if an internet connection is available."""
    try:
        requests.get("http://google.com")
        return True
    except requests.exceptions.ConnectionError:
        return False

class FileDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("File Downloader")
        # set icon
        self.root.iconbitmap("images\\standup_logo.ico")
        
        # Initialize the Google Drive API client
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_CREDENTIALS, scopes=['https://www.googleapis.com/auth/drive']
        )
        self.drive_service = build('drive', 'v3', credentials=credentials)

        
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        # Define the base directory where you want to save downloaded files
        self.download_dir = self.check_download_dir(config['DEFAULT']['DOWNLOAD_FOLDER_PATH'])
        
        

        # Create UI elements
        # create a box to hold the sync button and the sync icon
        self.sync_box = tk.Frame(root)
        self.sync_box.pack(pady=10)
        
        folder_location = ttk.Button(root, text="Open download folder", command=lambda: os.startfile(self.download_dir))
        folder_location.pack(in_=self.sync_box, side=tk.LEFT, padx=10)
        
        self.sync_button = ttk.Button(root, text="Sync", command=self.start_sync)
        self.sync_button.pack(in_=self.sync_box, side=tk.LEFT, padx=10)
        
        
        # Load icons
        scaleNum = 20
        syncIco = Image.open("images\\sync_icon.png")
        syncIco = syncIco.resize((scaleNum, scaleNum))
        self.sync_icon = ImageTk.PhotoImage(syncIco)
        checkIco = Image.open("images\\check_icon.png")
        checkIco = checkIco.resize((scaleNum, scaleNum))
        self.check_icon = ImageTk.PhotoImage(checkIco)

        # Create a label for the sync icon
        self.sync_icon_label = tk.Label(root)
        self.sync_icon_label.pack(in_=self.sync_box, side=tk.LEFT)

        self.log_window = scrolledtext.ScrolledText(root, width=40, height=20, wrap=tk.WORD)
        self.log_window.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        
        # self.start_sync()

    def start_sync(self):
        internet_access = internet_available()
        if internet_access:
            """Start the sync process"""
            print("Starting sync...")

            # Change the sync icon to the initial state
            self.sync_icon_label.config(image=self.sync_icon)
            self.sync_icon_label.update_idletasks()

            # Start a new thread for downloading
            self.download_folder_contents('root', self.download_dir)
            
            folder_struct =  self.list_folder_structure(self.drive_service)
            if len(folder_struct) > 0:
                self.start_sync()
            else:
                self.sync_icon_label.config(image=self.check_icon)
                self.sync_icon_label.update_idletasks()
                
                
            print("Sync complete")
        else:
            # show warning message
            messagebox.showwarning("No internet connection", "Please connect to the internet to sync files")

    def log_message(self, message):
        # Append a message to the log window
        self.log_window.insert(tk.END, f"{message}\n")
        self.log_window.yview(tk.END)  # Auto-scroll to the bottom
        # self.log_window.update_idletasks()
        # force the log window to update
        self.log_window.update()
        
    def list_folder_structure(self, service, folder_id='root'):
        """
        List the folder structure of Google Drive and return it as a JSON structure.

        Args:
        - service: The initialized Google Drive API service.
        - folder_id: The ID of the folder to start listing from (default is 'root' for the root folder).

        Returns:
        - A JSON structure representing the folder structure.
        """
        results = service.files().list(q=f"'{folder_id}' in parents", pageSize=1000).execute()
        items = results.get('files', [])

        folder_structure = []

        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                subfolder = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': 'folder',
                    'children': self.list_folder_structure(service, item['id'])  # Recursively list subfolders
                }
                folder_structure.append(subfolder)
            else:
                file = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': 'file'
                }
                folder_structure.append(file)

        return folder_structure
        
    def check_download_dir(self,dir):
        """Check if the download directory exists, if not ask the user to select a directory

        Args:
            dir (str): The download directory path
            
        Returns:
            dir (str): The download directory path
        """
        print(dir)
        if not os.path.exists(dir):
            # HIDE TKINTER WINDOW
            root = Tk()
            root.withdraw()
            
            response = messagebox.askokcancel("BeUpstanding Drive", f"Select which folder to download files to")
            if response:
                dir = filedialog.askdirectory()
                dir = self.check_download_dir(dir)
            else:
                quit()
        else:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            config['DEFAULT']['DOWNLOAD_FOLDER_PATH'] = dir
            # Write the updated config file
            with open(CONFIG_FILE, 'w') as config_file:
                config.write(config_file)
            return dir
        
    def get_files_in_folder(self, folder_id):
        """Get a list of files in a folder
        
        Args:
            folder_id (str): The ID of the folder to list files from
            
        Returns:
            files (list): A list of files in the folder
        """
            
        results = self.drive_service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        return files

    def download_file(self,file_id, file_name, parent_dir):
        """Download a file from Google Drive
        
        Args:
            file_id (str): The ID of the file to download
            file_name (str): The name of the file to download
            parent_dir (str): The path of the parent directory to download the file to
        """
        downloaded_file_path = os.path.join(parent_dir, file_name)
        request = self.drive_service.files().get_media(fileId=file_id)
        with open(downloaded_file_path, 'wb') as file:
            download_request = MediaIoBaseDownload(
                file, request
            )
            done = False
            while not done:
                status, done = download_request.next_chunk()
        print(f"File '{file_name}' downloaded successfully.")
        

    def check_file(self, file_id, file_name, parent_dir):
        """Check if the downloaded file matches the file on Google Drive using MD5 hash
        
        Args:
            file_id (str): The ID of the file to check
            file_name (str): The name of the file to check
            parent_dir (str): The path of the parent directory of the file
            
        Returns:
            bool: True if the file matches, False if it does not match
        """
        expected_md5 = self.drive_service.files().get(fileId=file_id, fields="md5Checksum").execute()['md5Checksum']
        downloaded_file_path = os.path.join(parent_dir, file_name)
        with open(downloaded_file_path, 'rb') as downloaded_file:
            md5 = hashlib.md5(downloaded_file.read()).hexdigest()
        if md5 == expected_md5:
            return True
        else:
            return False
        
    # Function to download files recursively
    def download_folder_contents(self, folder_id, parent_dir):
        """Download the contents of a folder from Google Drive recursively
        
        Args:
            folder_id (str): The ID of the folder to download
            parent_dir (str): The path of the parent directory to download the folder to
        """
        
        files = self.get_files_in_folder(folder_id)
        if not files and folder_id != 'root':
            # The folder is empty: delete it from Google Drive
            self.drive_service.files().delete(fileId=folder_id).execute()
            print(f"Folder '{parent_dir}' is empty. Deleting from Google Drive.")
            empty_folder = parent_dir.split(self.download_dir)[-1]
            self.log_message(f"Deleting empty google drive folder: '{empty_folder}'")
            
        for file in files:
            file_id = file['id']
            file_name = file['name']
            mime_type = file['mimeType']

            if mime_type == 'application/vnd.google-apps.folder':
                # Create a local directory for the folder and recursively download its contents
                folder_dir = os.path.join(parent_dir, file_name)
                if not os.path.exists(folder_dir):
                    os.makedirs(folder_dir)
                self.download_folder_contents(file_id, folder_dir)
            else:
                # check if the file already exists
                if os.path.exists(os.path.join(parent_dir, file_name)):
                    print(f"File '{file_name}' already exists. Skipping.")
                    self.log_message(f"Deleting '{file_name}' as it already exists. .")
                    #delete file from google drive
                    self.drive_service.files().delete(fileId=file_id).execute()
                else:
                    # Download and verify the file
                    self.download_file(file_id, file_name, parent_dir)
                        
                    # Verify the downloaded file using MD5 hash (you can use other hash algorithms)
                    file_good = self.check_file(file_id, file_name, parent_dir)
                    if file_good:
                        print(f"File '{file_name}' hash matches.")
                        self.log_message(f"Downloaded '{file_name}' successfully.")

                        #delete file from google drive
                        self.drive_service.files().delete(fileId=file_id).execute()
                    else:
                        print(f"File '{file_name}' hash does not match")
                        self.log_message(f"Failed to download '{file_name}'. Will retry later.")
                        #delete local file
                        os.remove(os.path.join(parent_dir, file_name))

if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloader(root)
    root.mainloop()
