import os
import pandas as pd
import pyarrow as pa 
import pyarrow.parquet as pq 
from tqdm import tqdm
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go


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
    print(f"Number of rows with missing data: {num_missing_rows}")    
    
    # print rows with missing data in any column
    print(data_frame[data_frame.isnull().any(axis=1)])
    
    #remove rows with missing data
    data_frame = data_frame.dropna()
    return data_frame

# -	Workday (start time at work, end time at work, total work hours) – 
#   as indicated by the first and last human presence (has the assumption they go to their desk first and last thing in the day)
def get_workday(data_frame):
    # return a list of start and end times for each workday
    workday = []
    date = data_frame['Date time'].dt.date.min()
    last_day = data_frame['Date time'].dt.date.max()
    print(date)
    # filter the data frame to only include data from that date
    day_data_frame = data_frame[data_frame['Date time'].dt.date == date]
   
    workdays = {}# {date: (start time, end time, duration)}
    while date < last_day:
        day_data_frame = data_frame[data_frame['Date time'].dt.date == date]
        # check if there is any human presence
        if day_data_frame[day_data_frame['Human Present'] == True].empty:
            date += timedelta(days=1)
            continue
        first_presence = day_data_frame[day_data_frame['Human Present'] == True].iloc[0]['Date time']
        last_presence = day_data_frame[day_data_frame['Human Present'] == True].iloc[-1]['Date time']     
        duration = last_presence - first_presence
        start_time = first_presence.time()
        end_time = last_presence.time()
        workdays[date] = (start_time, end_time, duration)
        date += timedelta(days=1)
    
    return workdays

def plot_workday(workdays):
    # plot the start time and end time against dates for each workday using plotly scatter
    fig = go.Figure()
    dates = list(workdays.keys())
    start_times = [workdays[date][0] for date in dates]
    end_times = [workdays[date][1] for date in dates]
    start_times_seconds = [time_to_seconds(t) for t in start_times]
    end_times_seconds = [time_to_seconds(t) for t in end_times]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=start_times_seconds, mode='markers', name='Start Time'))
    fig.add_trace(go.Scatter(x=dates, y=end_times_seconds, mode='markers', name='End Time'))

    # order y axis from 0 to 24 hours in seconds
    fig.update_yaxes(
        range=[0, 24*60*60],
        tickvals=list(range(0, 24*60*60, 60*60)),  # every hour
        ticktext=[f'{h}:00:00' for h in range(24)]  # labels for every hour
    )

    fig.show()
        
def time_to_seconds(t):
    return (t.hour * 60 + t.minute) * 60 + t.second

# -	Time at desk (and time away from desk: which would just be total work hours – time at desk). 
# -	Sitting time and standing time when at the desk (can covert to percentage like you have as we have work time. Pie graph that you did is useful).
# -	Number of sit-stand transitions during work time
# -	If you can do event files, it would also be great to know the bout durations (e.g., time spent sitting before getting up / transitioning away from desk). Bout durations we are particularly interested in are bouts of sitting longer than 30 minutes at a time. Bouts of standing it would be useful to know bouts longer than 30 minutes and bouts longer than 40 minutes (you are not supposed to stand more than 40 minutes at a time; we advocate for a 50:50 sitting:upright split hence the 30 minutes). 


if __name__ == "__main__":
    file_name = "merged_data.parquet"
    data_frame = load_from_parquet(file_name)
    data_frame = check_data(data_frame)
    work_days = get_workday(data_frame)
    plot_workday(work_days)