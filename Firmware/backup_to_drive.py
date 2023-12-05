"""
File: backup_to_drive.py
Description: This script contains functions to upload and download files to and from Google Drive.
Author: Sami Kaab
Date: 2023-07-05
"""

import os
import os.path
import shutil
import logging
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


from shared_resources import DATA_DIR,CONFIG_FILE,DEVICE_ID,ROOT_DIR

# Constants
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_credentials():
    """
    Get the user credentials for Google Drive.

    Returns:
        The user credentials for Google Drive.
    """
    # Check if a token file exists and load the credentials from it if it does
    creds = None
    creds = service_account.Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    
    return creds

def is_internet_available():
    """
    Check if there is internet access available.

    Returns:
        bool: True if internet access is available, False otherwise.
    """
    try:
        requests.get("http://google.com", timeout=5)
        # logging.info("Internet access available")
        return True
    except:
        # logging.error("No internet access available")
        return False

def delete_all():
    """
    Deletes all files in the user's Google Drive account using the Google Drive API.
    """
    # Set up the service account credentials
    credentials = get_credentials()

    # Build the Google Drive API client
    drive_service = build("drive", "v3", credentials=credentials)

    # List all files
    response = drive_service.files().list().execute()
    files = response.get("files", [])

    # Iterate through the files and delete them
    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        drive_service.files().delete(fileId=file_id).execute()
        print(f"Deleted file: {file_name}")
        

def create_folder(service, name, parent_folder_id=None):
    """
    Creates a new folder with the given name in Google Drive using the provided service object.
    If a folder with the same name already exists, returns its ID instead.

    Args:
        service: A Google Drive API service object.
        name (str): The name of the folder to create.
        parent_folder_id (str, optional): The ID of the parent folder to create the new folder in.

    Returns:
        str: The ID of the newly created folder or the existing folder with the same name.
    """
    # check if folder exists and return id if it does
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_folder_id:
        # if parent_folder_id is specified, add it to the query
        query += f" and '{parent_folder_id}' in parents"

    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    if len(response['files']) > 0:
        return response['files'][0]['id']
    
    
    folder_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]

    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder['id']

def upload_file(service, file_path, parent_folder_id):
    """
    Uploads a file to Google Drive.

    Args:
        service: Google Drive API service object.
        file_path: Path of the file to be uploaded.
        parent_folder_id: ID of the parent folder where the file will be uploaded.
        parent_folder_name: Name of the parent folder where the file will be uploaded (optional).

    Returns:
        ID of the uploaded file.
    """
    if service is None:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)
    # check if file exists and return id if it does
    query = f"name='{os.path.basename(file_path)}' and '{parent_folder_id}' in parents"
    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    if len(response['files']) > 0:
        return response['files'][0]['id']
    
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [parent_folder_id]
    }

    media = MediaFileUpload(file_path, mimetype='application/octet-stream')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    # logging.info(f"Backed up file: {file_path}")
    print(f"Backed up file: {file_path}")
    return file['id']




def clone_folder_structure(service, local_folder, parent_folder_id):
    """
    Recursively clones the folder structure of a local folder to a Google Drive folder.
    If a file with extension .csv is found, it is uploaded to the Google Drive folder.
    If the file already exists in the Google Drive folder, it is deleted from the local folder.

    Args:
        service: An authorized Google Drive API service instance.
        local_folder: The path of the local folder to be cloned.
        parent_folder_id: The ID of the parent folder in Google Drive.
    """
    
    folder_name = os.path.basename(local_folder)
    folder_id = create_folder(service, folder_name, parent_folder_id)

    for item in os.listdir(local_folder):
        item_path = os.path.join(local_folder, item)
        if os.path.isdir(item_path): # if item is a folder, recursively clone it
            # check if folder is empty
            if not os.listdir(item_path):
                # delete empty folder
                shutil.rmtree(item_path)
                print(f"Deleted empty folder: {item_path}")
            else:
                clone_folder_structure(service, item_path, folder_id)
        else: # if item is a file, upload it
            # check if file extension is .csv
            if item_path.endswith(".csv"):
                print(f"checking if {item_path} exists")
                file_exists = check_if_already_exist(item_path, service, folder_id)
                if not file_exists:
                    print(f"{item_path} does not exist: uploading")
                    upload_file(service, item_path, folder_id)
                else:
                    print(f"{item_path} already exists")
                    # delete file
                    os.remove(item_path)

def upload(drive_root_folder):
    """
    Uploads the contents of the DATA_DIR folder to Google Drive.

    Args:
        drive_root_folder (str): The name of the folder to create in Google Drive
            to store the backup.
    """
    # Get the user credentials for Google Drive
    creds = get_credentials()
    # Build the Google Drive API client with the user credentials
    service = build("drive", "v3", credentials=creds)
    drive_root_folder_id = create_folder(service, drive_root_folder)
    clone_folder_structure(service, DATA_DIR, drive_root_folder_id)
    
def check_if_already_exist(file_path, service, parent_folder_id):
    """
    Check if a file with the same name and size as 'file_path' already exists in the specified Google Drive folder.

    Args:
        file_path (str): The local file path to check.
        service: The Google Drive API service.
        parent_folder_id (str): The ID of the parent folder to check within.

    Returns:
        bool: True if a file with the same name and size exists, False otherwise.
    """
    file_name = os.path.basename(file_path)
    # Get the file size
    file_size = os.path.getsize(file_path)

    # Create a query to search for the file by name and parent folder
    query = f"name='{file_name}' and '{parent_folder_id}' in parents"

    # Execute the query and retrieve the list of matching files
    response = service.files().list(q=query, spaces='drive', fields='files(name, size)').execute()
    matching_files = response.get('files', [])

    # Check if any of the matching files have the same name and size
    for matching_file in matching_files:
        if matching_file['name'] == file_name and int(matching_file['size']) == file_size:
            return True

    return False

def delete_file(service, file_name):
    """
    Deletes a file from Google Drive.

    Args:
        service (Google Drive API service): The Google Drive API service.
        file_name (str): The name of the file to delete.

    Returns:
        bool: True if the file was deleted, False otherwise.
    """
    if service is None:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)
    # check if file exists and return id if it does
    query = f"name='{file_name}'"
    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    if len(response['files']) > 0:
        file_id = response['files'][0]['id']
        service.files().delete(fileId=file_id).execute()
        print(f"Deleted file: {file_name} (id: {file_id})")
        return True
    return False

def download_file(service, parent_folder_id, file_name, destination):
    """
    Downloads a file from Google Drive to a specified destination folder.

    Args:
        service: Google Drive API service object.
        parent_folder_id: ID of the parent folder containing the file to download.
        file_name: Name of the file to download.
        destination: Path to the destination folder where the file will be saved.

    Returns:
        True if the file was downloaded successfully, False otherwise.
    """
    
    if service is None:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)
    # check if file exists and return id if it does
    query = f"name='{file_name}' and '{parent_folder_id}' in parents"
    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    if len(response['files']) > 0:
        file_id = response['files'][0]['id']
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        file_path = os.path.join(destination, file_name)
        with open(file_path, "wb") as f:
            f.write(file_content)
        print(f"Downloaded file: {file_name} (id: {file_id})")
        return True
    
def backup_config_file(parent_folder_id=None, parent_folder_name=None):
    """
    Finds the ID of the configuration file in Google Drive and uploads a new version of the file.
    If the file already exists, it will be deleted before uploading the new version.

    Args:
        parent_folder_id (str): ID of the parent folder in Google Drive.
        parent_folder_name (str): Name of the parent folder in Google Drive.
    """
    file_id = None
    try:
        # find id of config file which parent folder is parent_folder_id or parent_folder_name
        print("finding config file id")
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)
        query = f"name='{os.path.basename(CONFIG_FILE)}'"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        elif parent_folder_name:
            parent_folder_id = create_folder(service, parent_folder_name)
            query += f" and '{parent_folder_id}' in parents"
                
                            
        response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        if len(response['files']) > 0:
            #get file id
            file_id = response['files'][0]['id']
        print("uploading config file to the internet")
        if file_id:
            #delete file
            service.files().delete(fileId=file_id).execute()
            print(f"Deleted file: {CONFIG_FILE}")
        # upload file
        upload_file(service, CONFIG_FILE, parent_folder_id)
    except Exception as e:
        print(e)
        
        
if __name__ == "__main__":
#     # setup_logging()
#     # os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # delete_all()
    # exit()

    # if is_internet_available():
        # upload()
    
    backup_config_file(parent_folder_name=DEVICE_ID)
    # backup_config_file(parent_folder_id='root')
    download_file(None, 'root', CONFIG_FILE, ROOT_DIR)