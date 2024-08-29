"""
This script is used to plot the standup data from the data frame between the start and end datetime

Author: Sami Kaab
Date: 5/12/2023
"""

from tkinter import filedialog
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

def plot_data(data_frame, start_datetime, end_datetime):
    """Summary: Plot the standup data from the data frame between the start and end datetime
    
    Args:
        data_frame (pandas.DataFrame): The data frame containing the standup data
        start_datetime (datetime.datetime): The start datetime to plot from
        end_datetime (datetime.datetime): The end datetime to plot to
    """
    # filter the data frame to only include data between the start and end datetime
    data_frame = data_frame[(data_frame['Date time'] > start_datetime) & (data_frame['Date time'] < end_datetime)]
    start_datetime = min(data_frame['Date time'])
    end_datetime = max(data_frame['Date time'])
    # plot the data using a bar chart where the height of the bar is the distance and the color is the human present. true is green, false is red
    fig = px.bar(data_frame, x='Date time', y='Distance(mm)', color='Human Present',
                 color_discrete_map={True: 'green', False: 'grey'})

    # set y axis range between 0 and the max distance
    fig.update_layout(
        yaxis_range=[0, 500],
        title_text=f"Standup Data from {start_datetime} to {end_datetime}",
        bargap=0.1,
        barmode='overlay'
        )
    fig.update_traces(marker_line_width=0)
    
    # show the figures
    fig.show()
    return fig
    
def load_data(root):
    """Summary: Load data from a directory containing CSV files and merge them into a single DataFrame
    
    Args:
        root (str): The path to the directory containing the CSV files
        
    Returns:
        pandas.DataFrame: A merged DataFrame containing the data from all the CSV files
    """
    # recursively get all the files in the directory that end with .csv
    fileList = [os.path.join(path, name) for path, subdirs, files in os.walk(root) for name in files if name.endswith(".csv")]
    # Loop through each file
    merged_df = pd.DataFrame()

    # Loop through each CSV file and append its data to the merged DataFrame
    for file_path in tqdm(fileList):
        df = pd.read_csv(file_path)
        #convert the date time column to a datetime object 24h format
        df['Date time'] = pd.to_datetime(df['Date time'], format='%Y-%m-%d %H:%M:%S')
        # Append the data to the merged DataFrame
        merged_df = pd.concat([merged_df, df], ignore_index=True)

    # Display the merged DataFrame
    print(merged_df)
    merged_df['Human Present'] = np.where(merged_df['Human Present'] == 0, False, True)
    return merged_df

def write_to_csv(data_frame, file_name):
    """Summary: Write the data frame to a csv file
    
    Args:   
        data_frame (pandas.DataFrame): The data frame to write
        file_name (str): The path to the output file
    """
    # print first few rows of the data frame
    print(data_frame.head())
    #convert the date time column to a string
    data_frame.to_csv(file_name, index=False)


if __name__ == "__main__":

    #open windows folder picker
    root = filedialog.askdirectory(title="Select the folder containing the participant data.", initialdir = os.getcwd())
    # check if there is a file called merged_data.csv in the folder
    if os.path.exists(os.path.join(root, "merged_data.csv")):
        #load the data from the file
        merged_df = pd.read_csv(os.path.join(root, "merged_data.csv"))
        # convert the date time column to a datetime object
        merged_df['Date time'] = pd.to_datetime(merged_df['Date time'], format='%Y-%m-%d %H:%M:%S')
    else:
        #load the data from the folder
        merged_df = load_data(root)
        destination = os.path.join(root, "merged_data.csv")
        write_to_csv(merged_df, destination)
    start = datetime(2023,11,17,8,0,0)
    stop = datetime(2023,11,30,17,0,0)
    fig = plot_data(merged_df, start, stop)
    # save plot to html
    pio.write_html(fig, os.path.join(root,"standup_data.html"))
    