# a script which defines a function to convert a list of cvs files into a single parquet file
import os
import pandas as pd
import pyarrow as pa 
import pyarrow.parquet as pq 
from tqdm import tqdm
from datetime import datetime, timedelta
import numpy as np



def load_data_from_csv(path_list):
    # Loop through each CSV file and append its data to the merged DataFrame
    merged_df = pd.DataFrame()
    for file_path in tqdm(path_list):
        df = pd.read_csv(file_path)
        # Append the data to the merged DataFrame
        merged_df = pd.concat([merged_df, df], ignore_index=True)
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
    
if __name__ == "__main__":
    # define the root directory
    root = "A17E\\data\\sk"
    current_dir = os.getcwd()   
    # recursively get all the files in the directory that end with .csv
    fileList = [os.path.join(path, name) for path, subdirs, files in os.walk(root) for name in files if name.endswith(".csv")]
    print(fileList)
    # load the data from the list of files
    merged_df = load_data_from_csv(fileList)
    print(merged_df.head())
    # process the data
    merged_df = process_data(merged_df)
    # write the data to a parquet file
    destination = os.path.join(current_dir, "merged_data.parquet")
    write_to_parquet(merged_df, destination)
    destination = os.path.join(current_dir, "merged_data.csv")
    write_to_csv(merged_df, destination)
    