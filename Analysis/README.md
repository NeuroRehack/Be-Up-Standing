## [🏠 HOME](../README.md) | [🔧 Firmware](../Firmware/README.md) | [💻 Software](../Software/README.md) | [📊 Analysis](./README.md)
This fodler contains a collection of Python scripts designed to process and analyze data collected from the standup device. The data analysis focuses on determining sitting and standing periods, transitions between these states, and human presence during work hours. The scripts generate detailed analysis results and visualizations, including time series plots, transitions, bouts, workday schedules, and time spent at or away from the desk.

## Scripts Overview

### 1. `convert.py`
The `convert.py` script is designed to batch process raw CSV data files by converting them into a more efficient Parquet format, which is better suited for subsequent analysis. This script is particularly useful when dealing with large datasets collected over multiple sessions.

#### Key Features:
- **Batch Processing**: Recursively identifies and processes all CSV files within a specified directory.
- **Session Management**: Groups files based on session identifiers derived from the filenames, ensuring that data from the same session is processed together.
- **Data Processing**: Merges the data from multiple files, converts datetime fields, and adjusts the data format for analysis.
- **Parallel Processing**: Utilizes multithreading to speed up the processing of multiple sessions simultaneously.
- **Output Formats**: Saves the processed data in both Parquet and CSV formats for flexibility in usage.

#### Usage:
1. **Input Directory Selection**: The script prompts the user to select a directory containing the raw CSV files.
2. **Output Directory Selection**: The user is prompted to select a directory where the processed files will be saved.
3. **Execution**: The script processes the files in batches, converting and saving them in the desired formats. Progress is displayed in real-time.

This script is essential for preparing raw data for analysis by ensuring it is organized, processed, and stored in a format that facilitates faster and more efficient analysis.

### 2. `main.py`

The `main.py` script serves as the primary entry point for analyzing standup data collected over a specified period. It automates the process of reading, processing, and generating visual analysis from data files, providing insights into user activity such as sitting, standing, and presence transitions. Read more about the data analysis workflow [here](#data-analysis-workflow).

#### Key Features:
- **Data Loading**: Reads standup data from Parquet files located in a user-specified directory.
- **Data Processing**: Cleans the data, removes outliers, and computes key metrics such as sitting and standing percentages, transitions between these states, and bouts of activity.
- **Analysis and Metrics**: Computes various metrics:
  -  Total data duration
  - Percentage of time spent sitting and standing each day
  - Sit-stand transitions
  - Presence transitions
  - Bouts of sitting and standing
  - Total time spent at the desk each day
- **Visualization**: Generates various plots to visualize the analyzed data, including time series plots, transition plots, workday summaries, and more.
- **Output**: Saves the generated plots as interactive HTML files in a user-specified output directory.

#### Usage:
1. **Directory Selection**: The script prompts the user to select directories for both input (where the data files are stored) and output (where results will be saved).
2. **Execution**: Once the directories are specified, the script processes all relevant data files, performs the analysis, and generates visualizations. Progress is displayed throughout the process.

Make sure to have run the `convert.py` script on the raw data files before using `main.py` for analysis.

### 3. `plotting.py`
The `plotting.py` script provides a collection of functions for generating detailed visualizations of standup data. It is used as a library of plotting functions by the main.py script to create various plots, including time series plots, transition plots, workday summaries, and more.

### 4. `analysis.py`
The `analysis.py` script contains functions that perform the core data analysis tasks on standup data. It includes functions for cleaning the data, computing metrics, identifying transitions, and calculating bouts of sitting and standing. These functions are used by the `main.py` script.

### 5. plot_standup_data.py
The `plot_standup_data.py` script is a standalone script that generates time series plots of standup data for a specified date range. It allows users to visualize the distance measurements and human presence data over time.
 


## Data Analysis Workflow 
<p align="center">
        <img src="../Documentation/Standup Data Analysis Flow Chart.png" width="400">
</p>

The data is initially loaded into a pandas DataFrame, where rows containing missing values are removed. To further clean the data, rows with outlier distance values are filtered out using a specified z-score threshold. This z-score represents the number of standard deviations a data point is from the mean. If a data point falls outside a predefined range (e.g., beyond ±4 standard deviations), it is classified as an outlier and removed. This step helps eliminate extreme values caused by brief manual handling of the device.

The data is then resampled at a defined interval (60 seconds in this case), which involves calculating rolling means for the 'Distance (mm)' column and determining the minimum value for the 'Human Present' column over each resampling period. This effectively returns `True` only if someone is present for more than a minute. Next, the start and end times of each workday are identified based on when human presence is first and last detected. Data points outside these computed work hours are filtered out, ensuring the analysis accurately captures the standing-to-sitting ratio during work hours, excluding any presence detected outside these times. The assumption is that any presence lasting longer than 60 seconds corresponds to the desk user, while shorter presences are disregarded.


The subsequent analysis is performed on the original, non-resampled data. A daily threshold for determining standing versus sitting is calculated based on distance measurements. This involves grouping the data by date and calculating the mean distance for each day, provided that the variability in distance measurements is sufficient. If the difference between the maximum and minimum distance values is smaller than a predefined threshold, the analysis flags the day as invalid by returning -1. These thresholds are then applied to the original data to classify whether the user is standing or sitting at each timestamp.

A new column, 'Standing,' is added to the DataFrame, where a value of `True` indicates the user is standing (distance greater than the threshold), and `False` indicates sitting. Transitions between sitting and standing are tracked by creating two new columns, 'TransitionToUP' and 'TransitionToDown.' The 'TransitionToUP' column flags transitions from sitting to standing, while 'TransitionToDown' flags the opposite. Additionally, transitions between presence and absence at the desk are captured in two more columns: 'PresentToAbsent' and 'AbsentToPresent.'

Several metrics are calculated to analyze the user's behavior. The total data duration is computed as the time span between the earliest and latest timestamps. The percentage of time spent sitting and standing each day, while the user is present, is calculated by dividing the time spent in each position by the total presence time. Sit-stand transitions are filtered to exclude transitions shorter than a specified minimum duration (120 seconds), ensuring that only significant changes are considered. Presence transitions, which track when the user arrives at or leaves the desk, are also filtered to retain only transitions lasting at least 60 seconds.

Finally, bouts of sitting and standing are calculated, considering both presence and height transitions. A bout is defined as a continuous period where the user is either sitting or standing while present at the desk. These bouts provide insights into uninterrupted sitting or standing periods. The total time spent at the desk each day is also calculated by summing all periods marked as 'Human Present,' offering a clear picture of the user's desk usage patterns.