import analysis
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from tqdm import tqdm
import os
from datetime import datetime, timedelta

def plot_data(data_frame, threshold =None, numdays = None):
    # filter the data frame to only include data between the start and end datetime
    # plot the data using a bar chart where the height of the bar is the distance and the color is the human present. true is green, false is red
    fig = px.bar(data_frame, x='Date time', y='Distance(mm)', color='Human Present',
                 color_discrete_map={True: 'green', False: 'grey'})
    # get max distance
    max_distance = max(data_frame['Distance(mm)'])

    # set y axis range between 0 and the max distance
    fig.update_layout(
        yaxis_range=[0, max_distance*1.2],
        title_text=f'Timeseries data for {numdays} days',
        bargap=0.1,
        barmode='overlay'
        )
    fig.update_traces(marker_line_width=0)
    # draw horizontal line at threshold
    if threshold is not None:
        fig.add_shape(
            dict(
                type="line",
                x0=min(data_frame['Date time']),
                y0=threshold,
                x1=max(data_frame['Date time']),
                y1=threshold,
                line=dict(
                    color="red",
                    width=3,
                ),
            )
        )
    
    # show the figures
    # save plot to html
    return fig
    
    
def plot_workday(workdays):
    # plot the start time and end time against dates for each workday using plotly scatter
    dates = list(workdays.keys())
    start_times = [workdays[date][0] for date in dates]
    end_times = [workdays[date][1] for date in dates]
    start_times_seconds = [analysis.time_to_seconds(t) for t in start_times]
    end_times_seconds = [analysis.time_to_seconds(t) for t in end_times]

    fig = go.Figure()
    # add vertical lines to show the range of work hours
    fig.add_trace(go.Scatter(x=dates, y=start_times_seconds, mode='markers', name='Start Time'))
    fig.add_trace(go.Scatter(x=dates, y=end_times_seconds, mode='markers', name='End Time'))
    for date, workday in workdays.items():
        sts = analysis.time_to_seconds(workday[0])
        ets = analysis.time_to_seconds(workday[1])
        fig.add_shape(
            dict(
                type="rect",
                x0=date,
                y0=sts,
                x1=date,
                y1=ets,
                line=dict(
                    color="rgba(170, 170, 170, 0.5)",
                    width=5,
                ),
            )
        )
        

    # order y axis from 0 to 24 hours in seconds
    fig.update_yaxes(
        range=[0, 24*60*60],
        tickvals=list(range(0, 24*60*60, 60*60)),  # every hour
        ticktext=[f'{h}:00:00' for h in range(24)]  # labels for every hour
    )
    # add title and labels
    fig.update_layout(title=f'Workday\ntime from first presence to last presence', xaxis_title='Date', yaxis_title='Time')
    # x tick every day

    return fig
    
def plot_time_at_desk(timeAtDesk):
    # plot stacke bar chart of time spent at desk and time spent away from desk {date:(time_at_desk, time_away_from_desk)}
    dates = list(timeAtDesk.keys())
    time_at_desk = [timeAtDesk[date][1] for date in dates]
    
    time_away_from_desk = [timeAtDesk[date][0] for date in dates]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=time_at_desk, name='Time at desk'))
    fig.add_trace(go.Bar(x=dates, y=time_away_from_desk, name='Time away from desk'))
    fig.update_layout(barmode='stack')
    fig.update_layout(title='Time at desk vs time away from desk')
    fig.update_xaxes(title='Date')
    # format axis hh:mm:ss
    fig.update_yaxes(tickvals=list(range(0, 24*60*60, 60*60)),  # every hour
                     ticktext=[f'{h}:00:00' for h in range(24)])  # labels for every hour
    return fig
    
if __name__ == "__main__":
    # fileName = "C:\\dps_out\\A3EB_1002.parquet"
    # fileName = "test.parquet"
    # fileNameBase = os.path.basename(fileName).split(".")[0]
    
    # data_frame = analysis.load_from_parquet(fileName)
    # data_frame = analysis.check_data(data_frame)

    # workDays = analysis.get_workday(data_frame)
    # timeAtDesk = analysis.get_time_at_desk(data_frame)
    # percStanding, threshold = analysis.get_sitting_and_standing_percentage(data_frame)
    # total_duration = analysis.get_data_duration(data_frame)
    
    # figures = {}
    # fig = plot_data(data_frame, numdays=total_duration.days, threshold=threshold)
    # figures["time_series"] = fig
    # fig = plot_workday(workDays)
    # figures["workday"] = fig
    # fig = plot_time_at_desk(timeAtDesk)
    # figures["time_at_desk"] = fig
    
    # for name, fig in figures.items():
    #     fig.show()
    #     # pio.write_html(fig, f"{fileNameBase}_{name}.html")
    # exit()
        
    input_dir = "C:\\dps_out_2"
    output_dir = "C:\\dps_out_2"
    completeFileList = [os.path.join(path, name) for path, subdirs, files in os.walk(input_dir) for name in files if name.endswith(".parquet")]
    

    for file in tqdm(completeFileList):
        data_frame = analysis.load_from_parquet(file)
        data_frame = analysis.check_data(data_frame)
        total_duration = analysis.get_data_duration(data_frame)
        file_base = os.path.basename(file) # get the file name without the path
        # get file name without extension
        file_base = os.path.splitext(file_base)[0]
        if total_duration > timedelta(hours=24):
            workDays = analysis.get_workday(data_frame)
            timeAtDesk = analysis.get_time_at_desk(data_frame)
            # percStanding, threshold = analysis.get_sitting_and_standing_percentage(data_frame)
            
            figures = {}
            fig = plot_data(data_frame, numdays = total_duration.days)
            figures["time_series"] = fig
            fig = plot_workday(workDays)
            figures["workday"] = fig
            fig = plot_time_at_desk(timeAtDesk)
            figures["time_at_desk"] = fig
            
            for name, fig in figures.items():
                outFile = os.path.join(output_dir, f"{file_base}_{name}.html")
                pio.write_html(fig, outFile)
    
    