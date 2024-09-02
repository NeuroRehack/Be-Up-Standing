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

def time_to_seconds(t):
    """Summary: This function converts a time object to seconds

    Args:
        t (datetime.time): The time object to convert

    Returns:
        int: The time in seconds
    """
    return (t.hour * 60 + t.minute) * 60 + t.second

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
    """Summary: This function reads a csv file and returns a pandas data frame

    Args:
        file_name (str): The path to the csv file

    Returns:
        pandas.DataFrame: The data frame read from the csv file
    """
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
    """Summary: This function removes data outside of work hours for each workday in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to remove data from
        workdays (dict): A dictionary with dates as keys and tuples of start and end times as values

    Returns:
        pandas.DataFrame: The data frame with data outside of work hours removed
    """
    # gorup dataframe by date and remove data outside of work hours using the remove_out_work_hours function
    data_frame = data_frame.groupby(data_frame['Date time'].dt.date).apply(remove_out_work_hours, workdays)
    
    # reset index
    data_frame = data_frame.reset_index(drop=True)
    return data_frame

def remove_out_work_hours(data_frame, workdays):
    """Summary: This function removes data outside of work hours for a single workday

    Args:
        data_frame (pandas.DataFrame): The data frame to remove data from
        workdays (dict): A dictionary with dates as keys and tuples of start and end times as values

    Returns:
        pandas.DataFrame: The data frame with data outside of work hours removed
    """
    # remove data outside of work hours an return the new data frame
    date = data_frame['Date time'].dt.date.iloc[0]
    if date not in workdays:
        return data_frame
    startTime = workdays[date][0]
    endTime = workdays[date][1]
    data_frame = data_frame[(data_frame['Date time'].dt.time >= startTime) & (data_frame['Date time'].dt.time <= endTime)]
    return data_frame

def resample_data(data_frame, resampling_period = 0):
    """Summary: This function resamples the data frame to a specified period
    
    Args:
        data_frame (pandas.DataFrame): The data frame to resample
        resampling_period (int, optional): The period to resample the data to in seconds. Defaults to 0.
        
    Returns:
        pandas.DataFrame: The resampled data frame
    """
    data_frame = data_frame.copy()
    if resampling_period == 0:
        return data_frame
    #get columns that are boolean
    bool_cols = data_frame.select_dtypes(include=[bool]).columns
    # compute sampling period base on date time of dta frame
    period = data_frame['Date time'].diff().median()
    if period.total_seconds() == 0:
        return data_frame
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
    
def get_data_for_date(data_frame, date):
    """Summary: This function filters the data frame to only include data from a specific date

    Args:
        data_frame (pandas.DataFrame): The data frame to filter
        date (datetime.date): The date to filter the data frame to

    Returns:
        pandas.DataFrame: The data frame with only data from the specified date
    """
    # filter the data frame to only include data from that date
    day_data_frame = data_frame[data_frame['Date time'].dt.date == date]
    return day_data_frame

def get_time_at_desk(data_frame):
    """Summary: This function computes the time at desk and time away from desk for each day in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the time at desk from

    Returns:
        dict: A dictionary with dates as keys and tuples of time away from desk and time at desk as values
    """
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
    # check if both columns exist in case there person is always away from desk or always at desk
    if len(time_at_desk.columns) < 2:
        return {}
        
    # rename the columns
    time_at_desk.columns = ['Time away from desk', 'Time at desk']
    
    # fill NaN values with timedelta 0 seconds
    time_at_desk = time_at_desk.fillna(timedelta(seconds=0))
    
    
    time_at_desk_dict = {} #{date: (time away from desk, time at desk)}
    for date, row in time_at_desk.iterrows():
        time_at_desk_dict[date] = (row['Time away from desk'].total_seconds(), row['Time at desk'].total_seconds())
    return time_at_desk_dict

def compute_sitting_and_standing(data_frame):
    """Summary: This function computes whether the person is sitting or standing based on the distance from the sensor and a threshold

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the sitting and standing from

    Returns:
        pandas.DataFrame: The data frame with a new column 'Standing' that is True if the person is standing and False if the person is sitting
    """
    data_frame = data_frame.copy()
    # create a new column 'Standing' that is True if 'Distance(mm)' is greater than the threshold for that date
    data_frame['Standing'] = np.where(data_frame['Distance(mm)'] > data_frame['Threshold'], True, False)
    return data_frame

def get_sitting_and_standing_percentage(data_frame):
    """Summary: This function computes the percentage of time the person is sitting and standing for each day
    
    Args:
        data_frame (pandas.DataFrame): The data frame to compute the sitting and standing percentage from
        
    Returns:
        dict: A dictionary with dates as keys and tuples of sitting and standing percentages as values
    """
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

def get_sit_stand_transitions(data_frame):
    """Summary: This function computes the sit to stand transitions and stand to sit transitions in the data frame
    
    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from
        
    Returns:
        dict: A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects
    """
    transitions = {}
    transitionToUpList = data_frame[data_frame['TransitionToUP'] == True]['Date time'].tolist()
    transitionsToDownList = data_frame[data_frame['TransitionToDown'] == True]['Date time'].tolist()
    transitions["TransitionToUP"] = transitionToUpList
    transitions["TransitionToDown"] = transitionsToDownList
    return transitions

def filter_transitions(transitions, minDuration, transitionName1, transitionName2):
    """Summary: This function filters the transitions that are less than minDuration seconds and merges transitions that are less than minDuration seconds with the 2 adjacent transitions

    Args:
        transitions (dict): A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects
        minDuration (int): The minimum duration in seconds for a transition
        transitionName1 (str): The name of the first transition
        transitionName2 (str): The name of the second transition

    Returns:
        dict: A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects
    """
    # filter transitions that are less than minDuration seconds
    #transition = {transitionName1: [datetime], transitionName2: [datetime]}
    # convert to {datetime: transitionName}
    transition = {}
    for dateTime in transitions[transitionName1]:
        transition[dateTime] = transitionName1
    for dateTime in transitions[transitionName2]:
        transition[dateTime] = transitionName2
    # sort the dictionary by date time
    transition = dict(sorted(transition.items()))
    dateTimes = list(transition.keys())
    # pair the datetimes together [1,2,3,4,5,6,7,8,9,10] -> [(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,10)]
    datePairs = [(dateTimes[i], dateTimes[i+1]) for i in range(len(dateTimes)-1)]
    # filter the pairs that are less than minDuration seconds. if a pair is less than minDuration seconds, merge the pair with the 2 adjacent pairs
    GoodPairs = []
    BadPairs = []
    for i, pair in enumerate(datePairs):
        if (pair[1] - pair[0]).total_seconds() < minDuration:
            BadPairs.append(pair)            
        else:
            GoodPairs.append(pair)
    goodList = []
    for pair in GoodPairs:
        goodList.append(pair[0])
        goodList.append(pair[1])
    badList = []
    for pair in BadPairs:
        badList.append(pair[0])
        badList.append(pair[1])
    dateList = []
    for dateTime in goodList:
        if dateTime not in badList and dateTime not in dateList:
            dateList.append(dateTime)
            
    newTransition = {transitionName1: [], transitionName2: []}
    for dateTime in dateList:
        key = transition[dateTime]
        value = dateTime
        newTransition[key].append(value)
        
    return newTransition

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
    """Summary: This function removes outliers from the data frame using the interquartile range. Outliers are defined as values that are outside of the range (Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)

    Args:
        data_frame (pandas.DataFrame): The data frame to remove outliers from
        outlierThreshold (float, optional): The number of interquartile ranges to consider as an outlier. Defaults to 1.5.

    Returns:
        pandas.DataFrame: The data frame with outliers removed
    """
    
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
    """Summary: This function computes the number of sit to stand transitions and stand to sit transitions for each day

    Args:
        transitions (dict): A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects

    Returns:
        dict: A dictionary with dates as keys and the number of transitions as values
    """
    daylyTransitions = {}#{date: number of transitions}
    for dateTime in transitions["TransitionToUP"]:
        date = dateTime.date()
        if date in daylyTransitions:
            daylyTransitions[date] += 1
        else:
            daylyTransitions[date] = 1
    return daylyTransitions

def compute_sit_stand_transitions(data_frame):
    """Summary: This function computes the sit to stand transitions and stand to sit transitions in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from

    Returns:
        dict: A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects
    """
    og_data_frame = data_frame.copy()
    # sort the data frame by 'Date time'
    data_frame = data_frame.sort_values('Date time')
    # group by date and apply transition computation to each group
    data_frame = data_frame.groupby(data_frame['Date time'].dt.date).apply(compute_daily_sit_stand_transitions).reset_index(drop=True)
    # merge og_data_frame with data_frame to get the original data frame with the new columns
    # data_frame = pd.merge(og_data_frame, data_frame[['Date time', 'TransitionToUP', 'TransitionToDown']], on='Date time', how='left')
    # set the new columns to False if they are NaN
    data_frame['TransitionToUP'] = data_frame['TransitionToUP'].fillna(False)
    data_frame['TransitionToDown'] = data_frame['TransitionToDown'].fillna(False)
    # merge absent to present and present to absent transitions
    data_frame['HeightTransition'] = data_frame['TransitionToUP'] | data_frame['TransitionToDown']  
    
    return data_frame

def compute_daily_sit_stand_transitions(data_frame):
    """Summary: This function computes the sit to stand transitions and stand to sit transitions in a group of data

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from

    Returns:
        pandas.DataFrame: The data frame with the new columns 'TransitionToUP' and 'TransitionToDown'
    """
    copied_dt = data_frame.copy()
    # add a new column 'Transition' that is True if 'Standing' has changed compared to the previous row
    copied_dt['TransitionToUP'] = (copied_dt['Standing'].ne(copied_dt['Standing'].shift())) & (copied_dt['Standing'] == True)   
    copied_dt['TransitionToDown'] = (copied_dt['Standing'].ne(copied_dt['Standing'].shift())) & (copied_dt['Standing'] == False) 
    # set the first row to False because there is no previous row to compare to
    copied_dt.loc[copied_dt.index[0], 'TransitionToUP'] = False
    copied_dt.loc[copied_dt.index[0], 'TransitionToDown'] = False
    return copied_dt.reset_index(drop=True)

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
    """Summary: This function computes the threshold for a vector of values

    Args:
        Vector (list): The vector of values to compute the threshold from
        minDistance (int, optional): The minimum distance between the maximum and minimum values for the threshold. Defaults to 0.

    Returns:
        int: The threshold for the vector of values
    """
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
    
def compute_present_to_absent_transitions(data_frame):
    """Summary: This function computes the present to absent and absent to present transitions in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from

    Returns:
        pandas.DataFrame: The data frame with the new columns 'PresentToAbsent' and 'AbsentToPresent'
    """
    data_frame = data_frame.copy()
    boolCols = data_frame.select_dtypes(include=[bool]).columns
    # group dataframe by date
    #print(data_frame[data_frame.isnull().any(axis=1)])
    data_frame = data_frame.groupby(data_frame['Date time'].dt.date).apply(compute_present_to_absent)
    #print(data_frame[data_frame.isnull().any(axis=1)])
    data_frame.loc[data_frame.index[0], 'AbsentToPresent'] = True
    # set the last row to True
    data_frame.loc[data_frame.index[-1], 'PresentToAbsent'] = True
    # reset index
    data_frame = data_frame.reset_index(drop=True)
    # create  a PresenceTransition column
    data_frame['PresenceTransition'] = data_frame['PresentToAbsent'] | data_frame['AbsentToPresent']
    # convert boolean columns to boolean
    data_frame[boolCols] = data_frame[boolCols].astype('bool')
    return data_frame

def compute_present_to_absent(data_frame):
    """ Summary: This function computes the present to absent and absent to present transitions in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from
        
    Returns:
        pandas.DataFrame: The data frame with the new columns 'PresentToAbsent' and 'AbsentToPresent'
    """
    data_frame = data_frame.copy()
    # add a new column 'PresentToAbsent' that is True if 'Human Present' has changed compared to the previous row
    data_frame['PresentToAbsent'] = (data_frame['Human Present'].ne(data_frame['Human Present'].shift())) & (data_frame['Human Present'] == False)
    data_frame['AbsentToPresent'] = (data_frame['Human Present'].ne(data_frame['Human Present'].shift())) & (data_frame['Human Present'] == True)

    # set the first row to False because there is no previous row to compare to
    data_frame.loc[data_frame.index[0], 'PresentToAbsent'] = False
    data_frame.loc[data_frame.index[0], 'AbsentToPresent'] = True
    # set the last row to True
    data_frame.loc[data_frame.index[-1], 'PresentToAbsent'] = True
    
    return data_frame.reset_index(drop=True)

def compute_bouts(transition, presenceTransition):
    """Summary: This function computes the bouts of sitting and standing for each day

    Args:
        transition (dict): A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects
        presenceTransition (dict): A dictionary of transitions with keys 'PresentToAbsent' and 'AbsentToPresent' that contain lists of datetime objects

    Returns:
        dict: A dictionary with dates as keys and a dictionary of bouts with keys 'Sitting' and 'Standing' as values
    """
    # create a dictionarry {datetime: "TransitionToUP" or "TransitionToDown" or "PresentToAbsent" or "AbsentToPresent"}
    transitionDict = {}
    for dateTime in transition["TransitionToUP"]:
        transitionDict[dateTime] = "TransitionToUP"
    for dateTime in transition["TransitionToDown"]:
        transitionDict[dateTime] = "TransitionToDown"
    for dateTime in presenceTransition["PresentToAbsent"]:
        transitionDict[dateTime] = "PresentToAbsent"
    for dateTime in presenceTransition["AbsentToPresent"]:
        transitionDict[dateTime] = "AbsentToPresent"
    # sort the dictionary by date time
    transitionDict = dict(sorted(transitionDict.items()))
    bout = {"Standing": [], "Sitting": []} # {Sitting: [(start, end),...], Standing: [(start, end),...]}
    present=False
    standing = False
    dateTimes = list(transitionDict.keys())
    transitionTypes = list(transitionDict.values())
    i = 0
    for dateTime, transition in transitionDict.items():
        #next dateTime
        if i < len(dateTimes)-1:
            nextDateTime = dateTimes[i+1]
        if transition == "PresentToAbsent":
            present = False
        elif transition == "AbsentToPresent":
            present = True
        elif transition == "TransitionToUP":
            standing = True
        elif transition == "TransitionToDown":
            standing = False
        if present:
            if standing:
                start = dateTime
                end  = nextDateTime
                bout["Standing"].append((start, end))
            else:
                start = dateTime
                end  = nextDateTime
                bout["Sitting"].append((start, end))
        i += 1
    return bout
                
def compute_daily_bouts(data_frame, transitionDict):
    """Summary: This function computes the bouts of sitting and standing for each day

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the bouts from
        transitionDict (dict): A dictionary of transitions with keys 'TransitionToUP' and 'TransitionToDown' that contain lists of datetime objects

    Returns:
        dict: A dictionary with dates as keys and a dictionary of bouts with keys 'Sitting' and 'Standing' as values
    """
    #set first row to True
    data_frame.loc[data_frame.index[0], 'Bout'] = True
    # for dateTime in transitionDict set bout to True
    for dateTime, transition in transitionDict.items():
        data_frame.loc[data_frame['Date time'] == dateTime, 'Bout'] = True
    return data_frame
        
def get_present_to_absent_transitions(data_frame, minDuration = 60):
    """Summary: This function computes the present to absent and absent to present transitions in the data frame

    Args:
        data_frame (pandas.DataFrame): The data frame to compute the transitions from
        minDuration (int, optional): The minimum duration in seconds for a transition. Defaults to 60.

    Returns:
        dict: A dictionary of transitions with keys 'PresentToAbsent' and 'AbsentToPresent' that contain lists of datetime objects
    """
    #return list of datetime of transitions
    presentToAbsentList = data_frame[data_frame['PresentToAbsent'] == True]['Date time'].tolist()
    absentToPresentList = data_frame[data_frame['AbsentToPresent'] == True]['Date time'].tolist()
    # sort the lists by date time
    presentToAbsentList.sort()
    absentToPresentList.sort()
    # if first absent to present is earlier than first present to absent, remove the first absent to present
    if len(absentToPresentList) > 0 and len(presentToAbsentList) > 0 and absentToPresentList[0] < presentToAbsentList[0]:
        absentToPresentList = absentToPresentList[1:]
    #pair the lists together -> [(present1, absent1), (present2, absent2), (present3, absent3)]
    presenceTransition = []
    for i in range(min(len(presentToAbsentList), len(absentToPresentList))):
        presenceTransition.append((presentToAbsentList[i], absentToPresentList[i]))
    # remove pair that are less than minDuration seconds
    presenceTransition = [pair for pair in presenceTransition if (pair[1] - pair[0]).total_seconds() >= minDuration]
    presentToAbsentList = [pair[0] for pair in presenceTransition]
    absentToPresentList = [pair[1] for pair in presenceTransition]
    return {"PresentToAbsent": presentToAbsentList, "AbsentToPresent": absentToPresentList}

def SummaryExport(output_dir, name, dailyTransitions, percStanding, workDays, bouts):
    """Summary: This function exports the summary data to a csv file

    Args:
        output_dir (str): The directory to save the csv file to
        name (str): The name of the csv file
        dailyTransitions (dict): A dictionary with dates as keys and the number of transitions as values
        percStanding (dict): A dictionary with dates as keys and a tuple of the percentage of time spent sitting and standing as values
        workDays (dict): A dictionary with dates as keys and tuples of start and end times as values
        bouts (dict): A dictionary with dates as keys and a dictionary of bouts with keys 'Sitting' and 'Standing' as values
    Returns:
        None
    """
    summaryData =  pd.DataFrame()   
    # create the columns of the summary data and fill with NaN
    summaryData['Transitions'] = np.nan
    summaryData['Standing %'] = np.nan    
    summaryData['Start time'] = np.nan
    summaryData['End time'] = np.nan
    summaryData['Work hours'] = np.nan
    summaryData['Number Sitting Bouts 30min or more'] = np.nan
    summaryData['Number Standing Bouts 40min or more'] = np.nan
    summaryData['Average Sitting Bout Duration'] = np.nan
    summaryData['Average Standing Bout Duration'] = np.nan
        
    for date, numTransitions in dailyTransitions.items():
        # add the number of transitions to the summary data
        summaryData.loc[date, 'Transitions'] = numTransitions
    
    for date, row in percStanding.items():
        # add the percentage of time spent standing to the summary data
        summaryData.loc[date, 'Standing %'] = row[1]*100
    
    for date, workDay in workDays.items():
        # add the start and end times of the workday to the summary data
        summaryData.loc[date, 'Start time'] = workDay[0]
        summaryData.loc[date, 'End time'] = workDay[1]
        workHours = time_to_seconds(workDay[1]) - time_to_seconds(workDay[0])
        #convert to time form HH:MM:SS
        summaryData.loc[date, 'Work hours'] = timedelta(seconds=workHours)
        
    # organise bouts by day {{Sitting: [(start, end),...], Standing: [(start, end),...]}} -> {date: {Sitting: [(start, end),...], Standing: [(start, end),...]}}
    dailyBouts = {}
    for boutsType, boutsList in bouts.items():
        for start, end in boutsList:
            date = start.date()
            if date not in dailyBouts:
                dailyBouts[date] = {"Sitting": [], "Standing": []}
            dailyBouts[date][boutsType].append((start, end))

   # compute the average duration of sitting bouts for each day
    for date, bouts in dailyBouts.items():
        cumDurationSitting = 0
        nbSittingBouts = len(bouts["Sitting"])
        nbSittingBoutsMoreThan30 = 0
        for start, end in bouts["Sitting"]:
            cumDurationSitting += (end - start).total_seconds()
            if (end - start).total_seconds() >= 1800:
                nbSittingBoutsMoreThan30 += 1
        if nbSittingBouts > 0:
            avgDurationSitting = cumDurationSitting/nbSittingBouts
        else:
            avgDurationSitting = 0
        # format average duration of sitting bouts to HH:MM:SS
        
        summaryData.loc[date, 'Average Sitting Bout Duration'] = timedelta(seconds=avgDurationSitting)    
        summaryData.loc[date, 'Number Sitting Bouts 30min or more'] = nbSittingBoutsMoreThan30
        cumDurationStanding = 0
        nbStandingBouts = len(bouts["Standing"])
        nbStandingBoutsMoreThan40 = 0
        for start, end in bouts["Standing"]:
            cumDurationStanding += (end - start).total_seconds()
            if (end - start).total_seconds() >= 2400:
                nbStandingBoutsMoreThan40 += 1
        if nbStandingBouts > 0:
            avgDurationStanding = cumDurationStanding/nbStandingBouts
        else:
            avgDurationStanding = 0
        summaryData.loc[date, 'Average Standing Bout Duration'] = timedelta(seconds=avgDurationStanding)
        summaryData.loc[date, 'Number Standing Bouts 40min or more'] = nbStandingBoutsMoreThan40
            
    
    # add missing dates to the summary data and fill with NaN
    # if transition number is Nan set standing to nan
    summaryData.loc[summaryData['Transitions'].isna(), 'Standing %'] = "NA"
    # if transition number is Nan set bout to nan
    summaryData.loc[summaryData['Transitions'].isna(), 'Number Sitting Bouts 30min or more'] = "NA"
    summaryData.loc[summaryData['Transitions'].isna(), 'Number Standing Bouts 40min or more'] = "NA"
    summaryData.loc[summaryData['Transitions'].isna(), 'Average Sitting Bout Duration'] = "NA"
    summaryData.loc[summaryData['Transitions'].isna(), 'Average Standing Bout Duration'] = "NA"
    
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
    #print(f"Summary data saved to {outputPath}")
    
def get_bouts(data_frame):
    """Summary: This function computes the bouts of sitting and standing for each day
    
    Args:
        data_frame (pandas.DataFrame): The data frame to compute the bouts from
        
    Returns:
        dict: A dictionary with keys 'SittingPresent' and 'StandingPresent' that contain lists of tuples of start and end times
    """
        
    data_frame = data_frame.copy()
    data_frame = data_frame[data_frame['Bout'] == True]
    data_frame = data_frame[data_frame['Human Present'] == True]
    # create a dictionary of bouts {SittingPresent: [(start, end),...], StandingPresent: [(start, end),...]}
    bouts = {"SittingPresent": [], "StandingPresent": []}
    return bouts

    

if __name__ == "__main__":

    file_name = "output//test.parquet"

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
    

    total_duration = get_data_duration(data_frame)
    percStanding = get_sitting_and_standing_percentage(data_frame)
    transition = get_sit_stand_transitions(data_frame)
    transition = filter_transitions(transition, minDuration=120, transitionName1="TransitionToUP", transitionName2="TransitionToDown")
    presenceTransition = get_present_to_absent_transitions(data_frame, minDuration=60)
    # presenceTransition = filter_transitions(presenceTransition , minDuration=60, transitionName1="AbsentToPresent", transitionName2="PresentToAbsent")
    bouts = compute_bouts(transition, presenceTransition)
    # print(presenceTransition)
    # bouts = get_bouts(data_frame)
    [print(bout) for bout in bouts.items()]
    # [print(bout) for bout in bouts.values()]

    dailyTransitions = get_num_of_daily_transition(transition)
        
    data_frame = resample_data(data_frame, 60)
    
    # timeAtDesk = get_time_at_desk(data_frame)
    
    # get name without extension from path
    name = os.path.splitext(os.path.basename(file_name))[0]

    SummaryExport(".", name, dailyTransitions, percStanding, workDays, bouts)