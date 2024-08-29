"""
This script takes a folder ID and a parent directory as arguments. It uses the Google Drive API to list all files in the given folder. 
If the folder is empty and not the root folder, it deletes the folder from Google Drive. For each file in the folder, it checks the MIME type. 
If the file is a folder, it creates a corresponding local directory and recursively downloads its contents. If the file is not a folder, it checks if the file already exists locally. 
If it does, it skips the download and deletes the file from Google Drive. If it doesn't, it downloads the file and verifies it using an MD5 hash. 
If the hash matches the expected hash, it deletes the file from Google Drive. If the hash does not match, it deletes the local file.



"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import hashlib
from tqdm import tqdm
import json
import configparser
from tkinter import messagebox,filedialog
from tkinter import Tk
from datetime import datetime, timedelta

def check_download_dir(dir):
    """Function to check if the download directory exists. If it does not exist, the user is prompted to select a directory to download files to.

    Args:
        dir (str): The directory path to check.
        
    Returns:
        str: The directory path to download files to.
    """
    print(dir)
    if not os.path.exists(dir):
        # HIDE TKINTER WINDOW
        root = Tk()
        root.withdraw()
        
        response = messagebox.askokcancel("BeUpstanding Drive", f"Select which folder to download files to")
        if response:
            dir = filedialog.askdirectory()
            dir = check_download_dir(dir)
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
    
    
def get_files_in_folder(folder_id):
    """Function to get all files in a folder.
    
    Args:
        folder_id (str): The ID of the folder to list files from.
        
    Returns:
        list: A list of files in the folder.
    """
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    return files

def download_file(file_id, file_name, parent_dir):
    """Function to download a file from Google Drive.
    
    Args:
        file_id (str): The ID of the file to download.
        file_name (str): The name of the file to download.
        parent_dir (str): The parent directory to save the file to.
    """
    
    downloaded_file_path = os.path.join(parent_dir, file_name)
    request = drive_service.files().get_media(fileId=file_id)
    with open(downloaded_file_path, 'wb') as file:
        download_request = MediaIoBaseDownload(
            file, request
        )
        done = False
        while not done:
            status, done = download_request.next_chunk()
    print(f"File '{file_name}' downloaded successfully.")

def check_file(file_id, file_name, parent_dir):
    """Function to check the integrity of a downloaded file using an MD5 hash.
    
    Args:
        file_id (str): The ID of the file to check.
        file_name (str): The name of the file to check.
        parent_dir (str): The parent directory where the file is saved.
        
    Returns:
        bool: True if the file hash matches the expected hash, False otherwise.
    """
    expected_md5 = drive_service.files().get(fileId=file_id, fields="md5Checksum").execute()['md5Checksum']
    downloaded_file_path = os.path.join(parent_dir, file_name)
    with open(downloaded_file_path, 'rb') as downloaded_file:
        md5 = hashlib.md5(downloaded_file.read()).hexdigest()
    if md5 == expected_md5:
        return True
    else:
        return False
    
# Function to download files recursively
def download_folder_contents(folder_id, parent_dir):
    """Function to download the contents of a folder from Google Drive.

    Args:
        folder_id (str): The ID of the folder to download.
        parent_dir (str): The parent directory to save the downloaded files to.
    """
    files = get_files_in_folder(folder_id)
    if not files and folder_id != 'root':
        # The folder is empty: delete it from Google Drive
        drive_service.files().delete(fileId=folder_id).execute()
        print(f"Folder '{parent_dir}' is empty. Deleting from Google Drive.")
    for file in files:
        file_id = file['id']
        file_name = file['name']
        mime_type = file['mimeType']

        if mime_type == 'application/vnd.google-apps.folder':
            # Create a local directory for the folder and recursively download its contents
            folder_dir = os.path.join(parent_dir, file_name)
            if not os.path.exists(folder_dir):
                os.makedirs(folder_dir)
            download_folder_contents(file_id, folder_dir)
        else:
            # check if the file already exists
            if os.path.exists(os.path.join(parent_dir, file_name)):
                print(f"File '{file_name}' already exists. Deleting.")
                #delete file from google drive
                drive_service.files().delete(fileId=file_id).execute()
            else:
                # Download and verify the file
                download_file(file_id, file_name, parent_dir)
                    
                # Verify the downloaded file using MD5 hash (you can use other hash algorithms)
                file_good = check_file(file_id, file_name, parent_dir)
                if file_good:
                    print(f"File '{file_name}' hash matches.")
                    #delete file from google drive
                    drive_service.files().delete(fileId=file_id).execute()
                else:
                    print(f"File '{file_name}' hash does not match")
                    #delete local file
                    os.remove(os.path.join(parent_dir, file_name))

def list_all_files():
    """Function to list all files in Google Drive.
    """
    results = drive_service.files().list(
        q="trashed=false",
        fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    if not files:
        print('No files found.')
    else:
        print('Files:')
        for file in files:
            print(f"{file['name']} ({file['id']})")
            
def list_folder_structure(service, folder_id='root'):
    """ List the folder structure of Google Drive and return it as a JSON structure.
       
        Args:
            service (googleapiclient.discovery.Resource): The initialized Google Drive API service.
            folder_id (str): The ID of the folder to start listing from (default is 'root' for the root folder).        
       
        Returns:
            list: A list of dictionaries representing the folder structure.
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
                'children': list_folder_structure(service, item['id'])  # Recursively list subfolders
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

def pretty_print_folder_structure(folder_structure):
    """Pretty-print the folder structure JSON with indentation.

    Args:
        folder_structure (list): A list of dictionaries representing the folder structure
        
    """
    print(json.dumps(folder_structure, indent=3))

def delete_all_files():
    """Function to delete all files and folders in Google Drive.
    
    """
    # recursively delete every file and folder in the drive
    results = drive_service.files().list(
        fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    if not files:
        print('No files found.')
    else:
        for file in tqdm(files):
            drive_service.files().delete(fileId=file['id']).execute()
            print(f"File '{file['name']}' deleted successfully.")

if __name__ == '__main__':
    # Define your service account credentials JSON file path
    SERVICE_ACCOUNT_CREDENTIALS = 'credentials.json'

    # Initialize the Google Drive API client
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_CREDENTIALS, scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build('drive', 'v3', credentials=credentials)

    CONFIG_FILE = "drive_settings.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # Define the base directory where you want to save downloaded files
    download_dir = check_download_dir(config['DEFAULT']['DOWNLOAD_FOLDER_PATH'])
    print(download_dir)
    
    folder_struct =  list_folder_structure(drive_service)
    pretty_print_folder_structure(folder_struct)
    print(len(folder_struct))
    while len(folder_struct) > 0:
        try:
            # print(folder_struct)
            pretty_print_folder_structure(folder_struct)
            
            # Start downloading from the root folder
            download_folder_contents('root', download_dir)
            folder_struct =  list_folder_structure(drive_service)
        except Exception as e:
            print(e)
            continue    
    print("All files downloaded successfully.")
