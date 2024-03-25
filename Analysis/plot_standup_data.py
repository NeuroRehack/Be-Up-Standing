# use plotly for plotting
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
        title_text='Standup Data',
        bargap=0.1,
        barmode='overlay'
        )
    fig.update_traces(marker_line_width=0)
    
    # get group data by height if above 200 and label it as standing or sitting
    data_frame_copy = data_frame.copy()
    data_frame_copy['Standing'] = np.where(data_frame_copy['Distance(mm)'] > 200, "standing", "sitting")
    
    start_datetime = start_datetime.strftime("%d/%m/%Y, %H:%M:%S")
    end_datetime = end_datetime.strftime("%d/%m/%Y, %H:%M:%S")
    # plot pie chart of standing vs sitting when human is present and set colors to green if standing and red if sitting
    fig2 = px.pie(data_frame_copy[data_frame_copy['Human Present'] == True], names='Standing', title=f'Standing vs Sitting between {start_datetime} and {end_datetime}', color='Standing', color_discrete_map={'standing': 'blue', 'sitting': 'grey'})
    
    # add label in pie chart
    fig2.update_traces(textposition='inside', textinfo='percent+label')
    # remove info on hover over pie chart
    fig2.update_traces(hoverinfo='none')
    # remove legend
    fig2.update_layout(showlegend=False)
    # show the figures
    fig.show()
    fig2.show()
    # save plot to html
    pio.write_html(fig, "standup_data.html")
    pio.write_html(fig2, "standup_data_pie.html")
    
def load_data(root):
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
    # print first few rows of the data frame
    print(data_frame.head())
    #convert the date time column to a string
    # data_frame['Date time'] = data_frame['Date time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    data_frame.to_csv(file_name, index=False)

    
    
# import the data
if __name__ == "__main__":

    root = "DriveData\\A17E\\data\\sk"
    root = "Z:\\Data\\DPS device"
    #open windows folder picker
    # root = filedialog.askdirectory(title="Select the folder containing the participant data.", initialdir = os.getcwd())
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
    start = datetime.now() - timedelta(days=50)
    stop = datetime.now()
    plot_data(merged_df, start, stop)