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
from scipy.stats import zscore
import scipy.stats as statstttttttttttt




def load_from_parquet(file_name):
    """Summary: This function reads a parquet file and returns a pandas data frame

    Args:
        file_name (str): The path to the parquet file

    Returns:
        pandas.DataFrame: The data frame read from the parquet file
    """
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
    """Summary: This function checks the data for missing values and removes rows with missing values

    Args:
        data_frame (pandas.DataFrame): The data frame to check for missing values

    Returns:
        pandas.DataFrame: The data frame with missing values removed
    """
    # Checks the data for missing values and removes rows with missing values
    
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
    """Summary: This function computes the start and end times of the workday for each workday in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the workday from

    Returns:
        dict: A dictionary with dates as keys and tuples of start and end times as values
    """
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


def remove_daily_out_work_hours(data_frame, workdays):
    # gorup dataframe by date and remove data outside of work hours using the remove_out_work_hours function
    data_frame = data_frame.groupby(data_frame['Date time'].dt.date).apply(remove_out_work_hours, workdays)
    
    # reset index
    data_frame = data_frame.reset_index(drop=True)
    return data_frame

def remove_out_work_hours(data_frame, workdays):
    # remove data outside of work hours an return the new data frame
    date = data_frame['Date time'].dt.date.iloc[0]
    if date not in workdays:
        return data_frame
    startTime = workdays[date][0]
    endTime = workdays[date][1]
    data_frame = data_frame[(data_frame['Date time'].dt.time >= startTime) & (data_frame['Date time'].dt.time <= endTime)]
    return data_frame
  
  

def resample_data(data_frame, resampling_period = 0):
    data_frame = data_frame.copy()
    if resampling_period == 0:
        return data_frame
    #get columns that are boolean
    bool_cols = data_frame.select_dtypes(include=[bool]).columns
    # compute sampling period base on date time of dta frame
    period = data_frame['Date time'].diff().median()
    # compute windows size so that the windo covers the resampling period
    window_size = int(resampling_period/period.total_seconds())
    # run rolling mean on distance and min on human present
    data_frame['Distance(mm)'] = data_frame['Distance(mm)'].rolling(window=window_size).mean()
    data_frame['Human Present'] = data_frame['Human Present'].rolling(window=window_size).min()
    #convert human present to boolean
    # set index
    data_frame = data_frame.set_index('Date time')
    # resample the data frame to the resampling period
    data_frame = data_frame.resample(f'{resampling_period}s').mean()
    # drop rows with missing values
    data_frame = data_frame.dropna()
    # reset index
    data_frame = data_frame.reset_index()
    # # convert 'Human Present' to boolean
    # data_frame['Human Present'] = np.where(data_frame['Human Present'] == 0, False, True)
    # convert boolean columns to boolean
    data_frame[bool_cols] = data_frame[bool_cols].astype('bool')
    return data_frame
    
    
def get_data_duration(data_frame):
    """Summary: This function computes the total duration of the data in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the duration from

    Returns:
        timedelta: The total duration of the data
    """
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
    # # # # # # print(data_frame.head())
    # get median time difference
    median_time_diff = data_frame['Time difference'].median()
    # # # # # # print(f"Median time difference: {median_time_diff}")
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
def compute_sitting_and_standing(data_frame):
    data_frame = data_frame.copy()
    # create a new column 'Standing' that is True if 'Distance(mm)' is greater than the threshold for that date
    data_frame['Standing'] = np.where(data_frame['Distance(mm)'] > data_frame['Threshold'], True, False)
    
    return data_frame

def get_sitting_and_standing_percentage(data_frame):
    data_frame = data_frame[data_frame['Human Present'] == True].copy()
    if data_frame.empty:
        return {}

    standing_time = data_frame.groupby([data_frame['Date time'].dt.date, 'Standing']).size()
    # unstack the multi-index series to get a dataframe with dates as index and 'Standing' as columns
    standing_time = standing_time.unstack()
    # check if both columns exist in case there person is always sitting or always standing
    if len(standing_time.columns) < 2:
        # add 'Sitting' column with all zeros if it doesn't exist
        standing_time[False] = 0
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
    return standing_time_dict

def compute_sit_stand_transitions(data_frame):
    """Summary: This function computes the sit to stand transitions and stand to sit transitions in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from

    Returns:
        dict: A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects
    """
    og_data_frame = data_frame.copy()
    # filter data frame to only include rows where 'Human Present' is True
    data_frame = data_frame[data_frame['Human Present'] == True].copy()
    # add a new column 'Date' that is the date part of 'Date time'
    # data_frame['Date'] = data_frame['Date time'].dt.date
    # sort the data frame by 'Date time'
    data_frame = data_frame.sort_values('Date time')
    # add a new column 'Transition' that is True if 'Standing' has changed compared to the previous row
    data_frame['TransitionToUP'] = (data_frame['Standing'].ne(data_frame['Standing'].shift())) & (data_frame['Standing'] == True)   
    data_frame['TransitionToDown'] = (data_frame['Standing'].ne(data_frame['Standing'].shift())) & (data_frame['Standing'] == False) 
    # merge og_data_frame with data_frame to get the original data frame with the new columns
    data_frame = pd.merge(og_data_frame, data_frame[['Date time', 'TransitionToUP', 'TransitionToDown']], on='Date time', how='left')
    # set the new columns to False if they are NaN
    data_frame['TransitionToUP'] = data_frame['TransitionToUP'].fillna(False)
    data_frame['TransitionToDown'] = data_frame['TransitionToDown'].fillna(False)
    #set the first row to False because there is no previous row to compare to
    data_frame.loc[0, 'TransitionToUP'] = False
    data_frame.loc[0, 'TransitionToDown'] = False
        # merge absent to present and present to absent transitions
    data_frame['HeightTransition'] = data_frame['TransitionToUP'] | data_frame['TransitionToDown']  
   
    return data_frame

def get_sit_stand_transitions(data_frame):
        #return dictionary of transitions {"TransitionToUP": [datetime], "TransitionToDown": [datetime]}
    transitions = {}
    transitionToUpList = data_frame[data_frame['TransitionToUP'] == True]['Date time'].tolist()
    transitionsToDownList = data_frame[data_frame['TransitionToDown'] == True]['Date time'].tolist()
    transitions["TransitionToUP"] = transitionToUpList
    transitions["TransitionToDown"] = transitionsToDownList
    return transitions

def filter_transitions(transitions, minDuration, transitionName1, transitionName2):
    # an up transition must be followed by a down transition and vice versa
    transitionToUpList = transitions[transitionName1]
    transitionsToDownList = transitions[transitionName2]
    if len(transitionToUpList) < 1 or len(transitionsToDownList) < 1:
        return transitions 
    transitionToUpList.sort()
    transitionsToDownList.sort()
    newUpList = []
    newDownList = []
    if transitionsToDownList[0] < transitionToUpList[0]:
        for i in range(len(transitionsToDownList)):
            if i < len(transitionToUpList):
                if  transitionToUpList[i] - transitionsToDownList[i] > timedelta(seconds=minDuration):
                    newUpList.append(transitionToUpList[i])
                    newDownList.append(transitionsToDownList[i])
                    
    else:
        for i in range(len(transitionToUpList)):
            if i < len(transitionsToDownList):
                if transitionsToDownList[i] - transitionToUpList[i] > timedelta(seconds=minDuration):
                    newUpList.append(transitionToUpList[i])
                    newDownList.append(transitionsToDownList[i])
    
        
    return {transitionName1: newUpList, transitionName2: newDownList}

def compute_daily_threshold(data_frame, minDistance = 200):
    """Summary: This function computes the daily threshold for each date in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the daily threshold from
        minDistance (int, optional): The minimum distance between the maximum and minimum values for the threshold. Defaults to 200.

    Returns:
        pandas.DataFrame: The data frame with the 'Threshold' column added
    """
    # get the daily threshold for each date and create a new column 'Threshold' that is the threshold for that date
    daily_threshold = data_frame.groupby(data_frame['Date time'].dt.date)['Distance(mm)'].apply(compute_threshold, minDistance)
    # add the threshold to the data frame
    data_frame['Threshold'] = data_frame['Date time'].dt.date.map(daily_threshold)
    return data_frame

def compute_threshold(Vector, minDistance = 0):
    # convert to numpy array  
    Vector = np.array(Vector)
    # # remove outliers
    # zscores = zscore(Vector)
    
    # Vector = Vector[abs(zscores) < outlierThreshold]
    if len(Vector) == 0 or Vector.max() - Vector.min() < minDistance:
        return -1
    # compute the threshold
    threshold = (Vector.max() + Vector.min())/1.2
    threshold = Vector.mean() #+ Vector.std()
    return threshold
    
def remove_outliers(data_frame, outlierThreshold = 3):
    """Summary: This function removes outliers from the data frame. Outliers are defined as values that are outlierThreshold standard deviations away from the mean.

    Args:
        data_frame (pandas.DataFrame): The data frame to remove outliers from
        outlierThreshold (int, optional): The number of standard deviations away from the mean to consider as an outlier. Defaults to 3.

    Returns:
        pandas.DataFrame: The data frame with outliers removed
    """
    # remove outliers from the data frame
    data_frame = data_frame[np.abs(zscore(data_frame['Distance(mm)'])) < outlierThreshold]
    return data_frame

def remove_outliers_irq(data_frame, outlierThreshold = 1.5):
    
    # remove outliers using the interquartile range
    # compute the first and third quartiles
    Q1 = data_frame['Distance(mm)'].quantile(0.25)
    Q3 = data_frame['Distance(mm)'].quantile(0.75)
    # compute the interquartile range
    IQR = Q3 - Q1
    # remove outliers from the data frame that are outside of the range (Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)
    data_frame = data_frame[(data_frame['Distance(mm)'] > (Q1 - outlierThreshold * IQR)) & (data_frame['Distance(mm)'] < (Q3 + outlierThreshold * IQR))]
    return data_frame

def remove_daily_outliers(data_frame, outlierThreshold = 3):
    """Summary: This function removes outliers from the data frame for each date. 
                Outliers are defined as values that are outlierThreshold standard deviations away from the mean.

    Args:
        data_frame (pandas.DataFrame): The data frame to remove outliers from
        outlierThreshold (int, optional): The number of standard deviations away from the mean to consider as an outlier. Defaults to 3.

    Returns:
        pandas.DataFrame: The data frame with outliers removed
    """
    # group data by date and remove outliers from each group
    # data_frame = data_frame.groupby(data_frame['Date time'].dt.date).apply(remove_outliers_irq, outlierThreshold)
    data_frame = data_frame.groupby(data_frame['Date time'].dt.date).apply(remove_outliers, outlierThreshold)
    # reset index
    data_frame = data_frame.reset_index(drop=True)
    return data_frame

def get_num_of_daily_transition(transitions):
    daylyTransitions = {}#{date: number of transitions}
    for dateTime in transitions["TransitionToUP"]:
        date = dateTime.date()
        if date in daylyTransitions:
            daylyTransitions[date] += 1
        else:
            daylyTransitions[date] = 1
    return daylyTransitions


def compute_present_to_absent_transitions(data_frame):
    data_frame = data_frame.copy()
    # add a new column 'PresentToAbsent' that is True if 'Human Present' has changed compared to the previous row
    data_frame['PresentToAbsent'] = (data_frame['Human Present'].ne(data_frame['Human Present'].shift())) & (data_frame['Human Present'] == False)
    data_frame['AbsentToPresent'] = (data_frame['Human Present'].ne(data_frame['Human Present'].shift())) & (data_frame['Human Present'] == True)
    data_frame.loc[0, 'PresentToAbsent'] = False
    data_frame.loc[0, 'AbsentToPresent'] = False
    data_frame['PresenceTransition'] = data_frame['PresentToAbsent'] | data_frame['AbsentToPresent']    
    
    return data_frame

def compute_bouts(data_frame):
    # a bout is a period of time where the person is either sitting or standing
    # a bout starts when the person changes from sitting to standing or vice versa or when the person is absent and becomes present or vice versa
    # a bout ends when the person changes from sitting to standing or vice versa or when the person is absent and becomes present or vice versa
    data_frame = data_frame.copy()
  
    # add a new column 'Bout' that is True if 'PresentToAbsent' or 'AbsentToPresent' or 'TransitionToUP' or 'TransitionToDown' is True
    data_frame['Bout'] = data_frame['PresenceTransition'] | data_frame['HeightTransition']
    data_frame['Bout'] = data_frame['Bout'].cumsum() # assign a unique number to each bout
    # merge bouts that are less than minDuration seconds
    return data_frame
    
     

def get_present_to_absent_transitions(data_frame):
    #return list of datetime of transitions
    presentToAbsentList = data_frame[data_frame['PresentToAbsent'] == True]['Date time'].tolist()
    absentToPresentList = data_frame[data_frame['AbsentToPresent'] == True]['Date time'].tolist()
    return {"PresentToAbsent": presentToAbsentList, "AbsentToPresent": absentToPresentList}




def noahSummaryExport(output_dir, name, dailyTransitions, percStanding, workDays):
    summaryData =  pd.DataFrame()   
    # add Date,Transitions,Standing as columns
    summaryData['Transitions'] = np.nan
    summaryData['Standing'] = np.nan    
    summaryData['Start time'] = np.nan
    summaryData['End time'] = np.nan
    summaryData['Work hours'] = np.nan
        
    for date, numTransitions in dailyTransitions.items():
        # add the number of transitions to the summary data
        summaryData.loc[date, 'Transitions'] = numTransitions
    
    for date, row in percStanding.items():
        # add the percentage of time spent standing to the summary data
        summaryData.loc[date, 'Standing'] = row[1]*100
    
    for date, workDay in workDays.items():
        # add the start and end times of the workday to the summary data
        summaryData.loc[date, 'Start time'] = workDay[0]
        summaryData.loc[date, 'End time'] = workDay[1]
        workHours = time_to_seconds(workDay[1]) - time_to_seconds(workDay[0])
        #convert to time form HH:MM:SS
        summaryData.loc[date, 'Work hours'] = timedelta(seconds=workHours)
        
    
    # add missing dates to the summary data and fill with NaN
    # if transition number is Nan set standing to nan
    summaryData.loc[summaryData['Transitions'].isna(), 'Standing'] = "NA"
    summaryData.loc[summaryData['Transitions'].isna(), 'Transitions'] = 0
    allDates = pd.date_range(start=summaryData.index.min(), end=summaryData.index.max())
    summaryData = summaryData.reindex(allDates)
    # reset index
    summaryData = summaryData.reset_index()
    # rename the columns
    summaryData = summaryData.rename(columns={'index': 'Date'})
    
    
    # #write summary data to csv
    outputPath = os.path.join(output_dir, f"summary_{name}.csv")
    summaryData.to_csv(outputPath, index=False)
    
    
def get_bouts(data_frame):
    # remove bouts smaller than 1 minute
    data_frame = data_frame.groupby('Bout').filter(lambda x: x['Date time'].count() > 1)
    # get bouts where bouts = {boutNumber: (start time, end time, durationSUM,durationDiff, sitting/standing, present/absent)}
    bouts = {}
    for boutNumber, bout in data_frame.groupby('Bout'):
        start_time = bout['Date time'].min()
        end_time = bout['Date time'].max()
        # duration in seconds as the sum of diff between adjacent date time where human present is true
        durationSum = bout[bout['Human Present'] == True]['Date time'].diff().dt.total_seconds().sum()
        durationDiff = (end_time - start_time).total_seconds() # duration in seconds as the difference between the start and end time
        diffBetween = durationDiff - durationSum
        #standing is true if any of the standing values is true
        standing = bout['Standing'].any()
        present = bout['Human Present'].any()
        bouts[boutNumber] = (start_time, end_time, durationSum, durationDiff, standing, present, diffBetween)
    return bouts


if __name__ == "__main__":

    file_name = "C:\\dps_out\\2009_9F56.parquet"
    file_name = "test.parquet"

    data_frame = load_from_parquet(file_name)
    data_frame = check_data(data_frame)
    data_frame = remove_daily_outliers(data_frame, outlierThreshold=4)
    
    resample_data_frame = resample_data(data_frame, 60)
    workDays = get_workday(resample_data_frame)
    data_frame = remove_daily_out_work_hours(data_frame, workDays)

    data_frame = compute_daily_threshold(data_frame, minDistance=150)
    data_frame = compute_sitting_and_standing(data_frame)
    data_frame = compute_sit_stand_transitions(data_frame)
    data_frame = compute_present_to_absent_transitions(data_frame)
    data_frame = compute_bouts(data_frame)
    
    print(data_frame.head())

    total_duration = get_data_duration(data_frame)
    percStanding = get_sitting_and_standing_percentage(data_frame)
    transition = get_sit_stand_transitions(data_frame)
    transition = filter_transitions(transition, minDuration=120, transitionName1="TransitionToUP", transitionName2="TransitionToDown")
    presenceTransition = get_present_to_absent_transitions(data_frame)
    presenceTransition = filter_transitions(presenceTransition , minDuration=60, transitionName1="AbsentToPresent", transitionName2="PresentToAbsent")
    # print(presenceTransition)
    bouts = get_bouts(data_frame)
    [print(bout) for bout in bouts.values()]

    
    dailyTransitions = get_num_of_daily_transition(transition)
        
    data_frame = resample_data(data_frame, 60)
    
    timeAtDesk = get_time_at_desk(data_frame)
    
    # get name without extension from path
    name = os.path.splitext(os.path.basename(file_name))[0]

    noahSummaryExport(".", name, dailyTransitions, percStanding, workDays)