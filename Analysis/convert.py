# a script which defines a function to convert a list of cvs files into a single parquet file
import os
import pandas as pd
import pyarrow as pa 
import pyarrow.parquet as pq 
from tqdm import tqdm
from datetime import datetime, timedelta
import numpy as np
import tkinter as tk
from tkinter import filedialog
import concurrent.futures



def load_data_from_csv(path_list):
    # Loop through each CSV file and append its data to the merged DataFrame
    merged_df = pd.DataFrame()
    for file_path in tqdm(path_list, desc="Loading data", dynamic_ncols=True):
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                continue
            # check if the data frame is empty
            # Append the data to the merged DataFrame
            merged_df = pd.concat([merged_df, df], ignore_index=True)
        except Exception as e:
            # print(f"Error reading file {file_path}: {e}")
            continue
    return merged_df

def process_data(data_frame):

    # convert the date time column to a datetime object
    data_frame['Date time'] = pd.to_datetime(data_frame['Date time'], format='%Y-%m-%d %H:%M:%S')
    data_frame['Human Present'] = np.where(data_frame['Human Present'] == 0, False, True)

    return data_frame

def write_to_parquet(data_frame, file_name):
    # write the data frame to a parquet file
    table = pa.Table.from_pandas(data_frame)
    pq.write_table(table, file_name)
    
def write_to_csv(data_frame, file_name):
    # write the data frame to a csv file
    data_frame.to_csv(file_name, index=False)
    
    
def get_session_file_paths(fileList):
    # csv file follow this naming pattern: deviceid_participant_date_time eg. A30A_0000_231102_160737.csv
    #create a dictionary to store the file paths where the patient id is the key and the value is a list of file paths
    
    session_files = {}
    for file in tqdm(fileList, desc="Processing files", dynamic_ncols=True):
        base_name = os.path.basename(file)
        # get the patient id from the file name
        patient_id = base_name.split("_")[1]
        device_id = base_name.split("_")[0]
        session_id = f"{patient_id}_{device_id}"
        if session_id not in session_files:
            session_files[session_id] = []
        session_files[session_id].append(file)
        
    return session_files

    
def process_session(session, fileList, outdir):
    # load the data from the list of files
    merged_df = load_data_from_csv(fileList)
    # process the data
    merged_df = process_data(merged_df)
    # write the data to a parquet file
    destination = os.path.join(outdir, f"{session}.parquet")
    write_to_parquet(merged_df, destination)
    destination = os.path.join(outdir, f"{session}.csv")
    write_to_csv(merged_df, destination)
    

def batch_process_files(input_dir, output_dir):
    # recursively get all the files in the directory that end with .csv
    completeFileList = [os.path.join(path, name) for path, subdirs, files in os.walk(input_dir) for name in files if name.endswith(".csv")]
    # get a dictionary with the session id as the key and a list of file paths as the value
    session_files = get_session_file_paths(completeFileList) 
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_session, session, fileList, output_dir): session for session, fileList in session_files.items()}
        progress = tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processing sessions", dynamic_ncols=True)
        for future in progress:
            session = futures[future]
            try:
                future.result()  # get the result or raise exception
            except Exception as e:
                print(f"Error processing session {session}: {e}")
   
if __name__ == "__main__":
    # input_dir = "A17E\\data\\sk"
    # session = "test"
    
    # fileList = [os.path.join(path, name) for path, subdirs, files in os.walk(input_dir) for name in files if name.endswith(".csv")]
    
    # process_session(session, fileList, ".")
    # exit()
    
    
    # define the root directory using tkinter folder picker
    
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select the folder containing the participant data")
    if not folder_selected:
        print("No folder selected. Exiting.")
        exit()
    outdir = filedialog.askdirectory(title="Select the output folder")
    if not outdir:
        print("No output folder selected. Exiting.")
        exit()

    batch_process_files(folder_selected, outdir)