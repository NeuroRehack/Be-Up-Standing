import os
import pandas as pd
import pyarrow as pa 
import pyarrow.parquet as pq 
from tqdm import tqdm
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
import tkinter as tk
from tkinter import filedialog


def load_from_parquet(file_name):
    # read the parquet file
    table = pq.read_table(file_name)
    # convert the table to a pandas data frame
    data_frame = table.to_pandas()
    return data_frame

def load_from_csv(file_name):
    # read the csv file
    data_frame = pd.read_csv(file_name)
    return data_frame

def check_data(data_frame):
    
    # get the number of rows with at least one missing value
    num_missing_rows = data_frame.isnull().any(axis=1).sum()
    # print(f"Number of rows with missing data: {num_missing_rows}")    
    
    # print rows with missing data in any column
    missing_data = data_frame[data_frame.isnull().any(axis=1)]
    # print(f"Mising data: {missing_data}\n------------")
    
    #remove rows with missing data
    data_frame = data_frame.dropna()
    return data_frame

# -	Workday (start time at work, end time at work, total work hours) – 
#   as indicated by the first and last human presence (has the assumption they go to their desk first and last thing in the day)
def get_workday(data_frame):
    # return a list of start and end times for each workday
    data_frame = data_frame.sort_values(by='Date time')
    data_frame = data_frame[data_frame['Human Present'] == True].copy()
    # group by date and get the first and last human presence
    workdays = data_frame.groupby(data_frame['Date time'].dt.date)['Date time'].agg(['first', 'last'])
    workdays = workdays.rename(columns={'first': 'Start time', 'last': 'End time'})
    
    workdaysdict = {}
    for date, row in workdays.iterrows():
        workdaysdict[date] = (row['Start time'].time(), row['End time'].time())
        
    return workdaysdict


def get_data_duration(data_frame):
    # get the total duration of the data
    start_time = data_frame['Date time'].min()
    end_time = data_frame['Date time'].max()
    duration = end_time - start_time
    return duration
    
        
def time_to_seconds(t):
    return (t.hour * 60 + t.minute) * 60 + t.second

def get_data_for_date(data_frame, date):
    # filter the data frame to only include data from that date
    day_data_frame = data_frame[data_frame['Date time'].dt.date == date]
    return day_data_frame

# -	Time at desk (and time away from desk: which would just be total work hours – time at desk). 
def get_time_at_desk(data_frame):
    # sort data_frame by date
    data_frame = data_frame.sort_values(by='Date time')
    # get the time difference betwween each row
    data_frame['Time difference'] = data_frame['Date time'].diff()
    print(data_frame.head())
    # get median time difference
    median_time_diff = data_frame['Time difference'].median()
    print(f"Median time difference: {median_time_diff}")
    # remove rows with time difference greater than 2*median time difference
    data_frame = data_frame[data_frame['Time difference'] < 2*median_time_diff]
    
    # shift 'Human Present' down by one row so that 'Time diff' corresponds to the time away from the desk
    data_frame['Human Present'] = data_frame['Human Present'].shift()
    
    # group by date and 'Human Present' and sum if 'Human Present' is True
    time_at_desk = data_frame.groupby([data_frame['Date time'].dt.date, 'Human Present'])['Time difference'].sum()
    
    # unstack the multi-index series to get a dataframe with dates as index and 'Human Present' as columns
    time_at_desk = time_at_desk.unstack()
    
    # rename the columns
    time_at_desk.columns = ['Time away from desk', 'Time at desk']
    
    # fill NaN values with timedelta 0 seconds
    time_at_desk = time_at_desk.fillna(timedelta(seconds=0))
    
    
    time_at_desk_dict = {} #{date: (time away from desk, time at desk)}
    for date, row in time_at_desk.iterrows():
        time_at_desk_dict[date] = (row['Time away from desk'].total_seconds(), row['Time at desk'].total_seconds())
    return time_at_desk_dict

# -	Sitting time and standing time when at the desk (can covert to percentage like you have as we have work time. Pie graph that you did is useful).
def get_sitting_and_standing_percentage(data_frame):
    # filter data frame to only include rows where 'Human Present' is True
    data_frame = data_frame[data_frame['Human Present'] == True].copy()
    # compute a threshold for Distance(mm) to determine if the person is sitting or standing
    threshold = data_frame['Distance(mm)'].mean()
    # create a new column 'Standing' that is True if 'Distance(mm)' is greater than the threshold
    data_frame['Standing'] = np.where(data_frame['Distance(mm)'] > threshold, True, False)
    # group by date and 'Standing' and count the number of rows
    standing_time = data_frame.groupby([data_frame['Date time'].dt.date, 'Standing']).size()
    # unstack the multi-index series to get a dataframe with dates as index and 'Standing' as columns
    standing_time = standing_time.unstack()
    # rename the columns
    standing_time.columns = ['Sitting', 'Standing']
    # fill NaN values with 0
    standing_time = standing_time.fillna(0)
    # convert to percentage
    standing_time['Total'] = standing_time['Sitting'] + standing_time['Standing']
    standing_time['Sitting'] = standing_time['Sitting'] / standing_time['Total']
    standing_time['Standing'] = standing_time['Standing'] / standing_time['Total']
    # convert to dictionary
    standing_time_dict = {} #{date: (sitting time, standing time)}
    for date, row in standing_time.iterrows():
        standing_time_dict[date] = (row['Sitting'], row['Standing'])
    return standing_time_dict, threshold

# -	Number of sit-stand transitions during work time
def get_sit_stand_transitions(data_frame):
    # filter data frame to only include rows where 'Human Present' is True
    data_frame = data_frame[data_frame['Human Present'] == True].copy()
    # compute a threshold for Distance(mm) to determine if the person is sitting or standing
    threshold = data_frame['Distance(mm)'].mean()
    # create a new column 'Standing' that is True if 'Distance(mm)' is greater than the threshold
    data_frame['Standing'] = np.where(data_frame['Distance(mm)'] > threshold, True, False)
    # compute the number of sit-stand transitions
    transitions = data_frame['Standing'].diff().abs().sum()
    return transitions

def get_bouts(data_frame):
    """
    Get sitting and standing bouts
    returns: 
        a dictionary with date as key and a dictionary as value with 'sitting' and 'standing' as keys and 
        a list of tuples corresponding to the start and end time of each bout 
    """
    # filter data frame to only include rows where 'Human Present' is True
    data_frame = data_frame[data_frame['Human Present'] == True].copy()
    # compute a threshold for Distance(mm) to determine if the person is sitting or standing
    threshold = data_frame['Distance(mm)'].mean()
    # create a new column 'Standing' that is True if 'Distance(mm)' is greater than the threshold
    data_frame['Standing'] = np.where(data_frame['Distance(mm)'] > threshold, True, False)

    # convert 'Date time' to datetime if it's not already
    data_frame['Date time'] = pd.to_datetime(data_frame['Date time'])

    # create a new column 'Bout' that is True when 'Standing' changes
    data_frame['Bout'] = data_frame['Standing'].diff().ne(0)

    # group by date, 'Standing', and 'Bout' and get the first and last 'Date time' in each group
    bouts = data_frame.groupby([data_frame['Date time'].dt.date, 'Standing', 'Bout'])['Date time'].agg(['first', 'last'])

    # create a dictionary with date as key and a dictionary as value with 'sitting' and 'standing' as keys and 
    # a list of tuples corresponding to the start and end time of each bout
    bouts_dict = {}
    for (date, standing, _), (start, end) in bouts.iterrows():
        if date not in bouts_dict:
            bouts_dict[date] = {'sitting': [], 'standing': []}
        bouts_dict[date]['standing' if standing else 'sitting'].append((start, end))

    return bouts_dict

    
    


if __name__ == "__main__":
    test = True
    if test:
        file_name = "test.parquet"
        data_frame = load_from_parquet(file_name)
        data_frame = check_data(data_frame)
        total_duration = get_data_duration(data_frame)
        file_base = os.path.basename(file_name) # get the file name without the path
        print(f"Total duration of {file_base}: {total_duration}")
        work_days = get_workday(data_frame)
        timeAtDesk = get_time_at_desk(data_frame)
        percStanding, threshold = get_sitting_and_standing_percentage(data_frame)
        bouts = get_bouts(data_frame)
        
        for date, (start_time, end_time) in work_days.items():
            print(f"Date: {date}, Start time: {start_time}, End time: {end_time}")
        for date, (time_away_from_desk, time_at_desk) in timeAtDesk.items():
            print(f"Date: {date}, Time away from desk: {time_away_from_desk}, Time at desk: {time_at_desk}")
        # for date, (sitting_time, standing_time) in percStanding.items():
        #     print(f"Date: {date}, Sitting time: {sitting_time}, Standing time: {standing_time}")
        # for date, bouts_dict in bouts.items():
        #     print(f"Date: {date}")
        #     for standing, bouts_list in bouts_dict.items():
        #         print(f"{standing}: {bouts_list}")
                
                
        # write results to csv
        # date, start_time, end_time, time_away_from_desk, time_at_desk, sitting_time, standing_time
        results = []
        for date, (start_time, end_time) in work_days.items():
            time_away_from_desk, time_at_desk = timeAtDesk[date]
            sitting_perc, standing_perc = percStanding[date]
            results.append([date, start_time, end_time, time_away_from_desk, time_at_desk, sitting_perc, standing_perc, threshold])
        results_df = pd.DataFrame(results, columns=['Date', 'Start time', 'End time', 'Time away from desk', 'Time at desk', 'Sitting perc', 'Standing perc', 'Threshold'])
        results_df.to_csv("results.csv", index=False)
  
        
        exit()

    
    # input_dir = filedialog.askdirectory()
    # if not input_dir:
    #     print("No folder selected. Exiting.")
    #     exit()
    # output_dir = filedialog.askdirectory()
    # if not output_dir:
    #     print("No folder selected. Exiting.")
    #     exit()
    input_dir = "C:\\dps_out"
    output_dir = "C:\\dps_out"
    completeFileList = [os.path.join(path, name) for path, subdirs, files in os.walk(input_dir) for name in files if name.endswith(".parquet")]
    

    for file in tqdm(completeFileList):
        data_frame = load_from_parquet(file)
        data_frame = check_data(data_frame)
        total_duration = get_data_duration(data_frame)
        file_base = os.path.basename(file) # get the file name without the path
        # get file name without extension
        file_base = os.path.splitext(file_base)[0]
        if total_duration > timedelta(hours=48):
            print(f"Total duration of {file_base}: {total_duration}")
            work_days = get_workday(data_frame)
            work_days = get_workday(data_frame)
            timeAtDesk = get_time_at_desk(data_frame)
            percStanding, threshold = get_sitting_and_standing_percentage(data_frame)
            results = []
            for date, (start_time, end_time) in work_days.items():
                time_away_from_desk, time_at_desk = timeAtDesk[date]
                sitting_perc, standing_perc = percStanding[date]
                results.append([date, start_time, end_time, time_away_from_desk, time_at_desk, sitting_perc, standing_perc, threshold])
            results_df = pd.DataFrame(results, columns=['Date', 'Start time', 'End time', 'Time away from desk', 'Time at desk', 'Sitting perc', 'Standing perc', 'Threshold'])
            results_df.to_csv(os.path.join(output_dir,f"results_{file_base}.csv"), index=False)
            
  