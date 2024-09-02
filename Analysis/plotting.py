import analysis
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from tqdm import tqdm
import os
from datetime import datetime, timedelta

# data_frame example
#                 Date time  Distance(mm)  Human Present   Threshold  Standing  TransitionToUP  TransitionToDown  PresentToAbsent  AbsentToPresent  Bout
# 0     2023-11-17 12:36:02         364.0           True  295.087819      True           False             False            False            False     0
# 1     2023-11-17 12:36:07         364.0           True  295.087819      True           False             False            False            False     0
# 2     2023-11-17 12:36:13         363.0           True  295.087819      True           False             False            False            False     0
# 3     2023-11-17 12:36:18         363.0           True  295.087819      True           False             False            False            False     0
# 4     2023-11-17 12:36:23         363.0           True  295.087819      True           False             False            False            False     0
# ...                   ...           ...            ...         ...       ...             ...               ...              ...              ...   ...
# 62693 2023-11-30 11:17:17         353.0           True  149.232044      True           False             False            False            False   596
# 62694 2023-11-30 11:17:27         356.0           True  149.232044      True           False             False            False            False   596
# 62695 2023-11-30 11:17:37         352.0           True  149.232044      True           False             False            False            False   596
# 62696 2023-11-30 11:17:49         354.0           True  149.232044      True           False             False            False            False   596
# 62697 2023-11-30 11:17:59         351.0           True  149.232044      True           False             False            False            False   596

def plot_data(data_frame, numdays = None):
    """Summary: Plot the data frame using a bar chart where the height of the bar is the distance and the color is the human present. true is green, false is red
        
        Args:
            data_frame (pandas.DataFrame): data frame to plot
            numdays (int): number of days to plot
        
        Returns:
            fig (plotly.graph_objects.Figure): plotly figure object
    """
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
    return fig

def plot_threshold(data_frame,fig):
    """Summary: Draw horizontal line at daily threshold. overlay the line on the existing figure

    Args:
        data_frame (pandas.DataFrame): data frame to plot
        fig (plotly.graph_objects.Figure): plotly figure object
        
    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
    #get threshold for each day and put it in a dictionary {date:threshold}
    thresholdDates = data_frame.groupby(data_frame['Date time'].dt.date)['Threshold'].mean()
    thresholdDates = thresholdDates.to_dict()
    #draw horizontal line at daily threshold. overlay the line on the existing figure
    for date, threshold in thresholdDates.items():
        nextDay = date + timedelta(days=1)
        fig.add_shape(
            dict(
                type="line",
                x0=date,
                y0=threshold,
                # date + timedelta(days=1)
                x1=nextDay,
                y1=threshold,
                line=dict(
                    color="red",
                    width=3,
                ),
            )
        )
        # add legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='red'), name='Threshold'))
    return fig

def plot_transitions(fig, transition, max_distance = 1000):
    """Summary: Draw vertical lines at transitions. blue for transition to standing, purple for transition to sitting

    Args:
        fig (plotly.graph_objects.Figure): plotly figure object
        transition (dict): dictionary of transitions {TransitionToUP: [date1, date2, ...], TransitionToDown: [date1, date2, ...]}
        max_distance (int, optional): max distance to plot. Defaults to 1000.

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
    # draw vertical lines at transitions
    # blue for transition to standing
    # purple for transition to sitting
    transitionUP = transition["TransitionToUP"]
    for date in transitionUP:
        fig.add_shape(
            dict(
                type="line",
                x0=date,
                y0=0,
                x1=date,
                y1=max_distance,
                line=dict(
                    color="blue",
                    width=1,
                ),
            )
        )
    transitionDown = transition["TransitionToDown"]
    for date in transitionDown:
        fig.add_shape(
            dict(
                type="line",
                x0=date,
                y0=0,
                x1=date,
                y1=max_distance,
                line=dict(
                    color="purple",
                    width=1,
                ),
            )
        )
    # add legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='blue'), name='Transition to standing'))

    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='purple'), name='Transition to sitting'))
    return fig

def plot_presence_transitions(fig, transition, max_distance = 1000):
    """Summary: Draw vertical lines at transitions. blue for transition to standing, purple for transition to sitting

    Args:
        fig (plotly.graph_objects.Figure): plotly figure object
        transition (dict): dictionary of transitions {PresentToAbsent: [date1, date2, ...], AbsentToPresent: [date1, date2, ...]}
        max_distance (int, optional): max distance to plot. Defaults to 1000.

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
    # draw vertical lines at transitions
    # blue for transition to standing
    # purple for transition to sitting
    transitionUP = transition["PresentToAbsent"]
    for date in transitionUP:
        fig.add_shape(
            dict(
                type="line",
                x0=date,
                y0=0,
                x1=date,
                y1=max_distance,
                line=dict(
                    color="black",
                    width=1,
                ),
            )
        )
    transitionDown = transition["AbsentToPresent"]
    for date in transitionDown:
        fig.add_shape(
            dict(
                type="line",
                x0=date,
                y0=0,
                x1=date,
                y1=max_distance,
                line=dict(
                    color="red",
                    width=1,
                ),
            )
        )
    # add legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='black'), name='Present to Absent'))

    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='red'), name='Absent to Present'))
    return fig
      
def plot_workday(workdays):
    """Summary: Plot the start time and end time against dates for each workday using plotly scatter

    Args:
        workdays (dict): dictionary of workdays {date: (start_time, end_time)}

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
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
        ticktext=[f'{h}:00:00' for h in range(24)],  # labels for every hour
        autorange="reversed"
    )
    # add title and labels
    fig.update_layout(title=f'Workday\ntime from first presence to last presence', xaxis_title='Date', yaxis_title='Time')
    # x tick every day

    return fig
    
def plot_time_at_desk(timeAtDesk):
    """Summary: Plot stacke bar chart of time spent at desk and time spent away from desk {date:(time_at_desk, time_away_from_desk)}

    Args:
        timeAtDesk (dict): dictionary of time spent at desk and time spent away from desk {date:(time_at_desk, time_away_from_desk)}

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
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

def plot_sitting_and_standing_percentage(percStanding):
    """Summary: Plot the percentage of time spent sitting and standing for each date

    Args:
        percStanding (dict): dictionary of percentage of time spent sitting and standing for each date

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
    # plot the percentage of time spent sitting and standing for each date
    fig = go.Figure()
    dates = list(percStanding.keys())
    sitting_percentage = [percStanding[date][0]*100 for date in dates]
    standing_percentage = [percStanding[date][1]*100 for date in dates]
    fig.add_trace(go.Bar(x=dates, y=sitting_percentage, name='Sitting Percentage'))
    fig.add_trace(go.Bar(x=dates, y=standing_percentage, name='Standing Percentage'))
    fig.update_layout(barmode='stack')
    # compute overall sitting and standing percentage
    overall_sitting_percentage = sum(sitting_percentage)/len(sitting_percentage)
    overall_standing_percentage = sum(standing_percentage)/len(standing_percentage)
    fig.update_layout(title='Sitting vs Standing percentage<br>Overall sitting percentage: {:.2f}%<br>Overall standing percentage: {:.2f}%'.format(overall_sitting_percentage, overall_standing_percentage))
    fig.update_xaxes(title='Date')
    fig.update_yaxes(title='Percentage')

    # new line symbol in html
    
    return fig

def plot_transition(transition):
    """Summary: Plot the number of transitions between sitting and standing for each date

    Args:
        transition (dict): dictionary of transitions {TransitionToUP: [date1, date2, ...], TransitionToDown: [date1, date2, ...]}

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
    # plot the number of transitions between sitting and standing for each date
    fig = go.Figure()
    dates = list(transition.keys())
    transitions = [transition[date] for date in dates]
    fig.add_trace(go.Bar(x=dates, y=transitions, name='Transitions'))
    fig.update_layout(title='Number of transitions between sitting and standing')
    fig.update_xaxes(title='Date')
    fig.update_yaxes(title='Number of transitions')
    return fig

def plot_bouts(fig, bouts):
    """Summary: Plot horizontal line for each bout : bouts {SittingPresent: [(start, end),...], StandingPresent: [(start, end),...]}

    Args:
        fig (plotly.graph_objects.Figure): plotly figure object
        bouts (dict): dictionary of bouts {SittingPresent: [(start, end),...], StandingPresent: [(start, end),...]}

    Returns:
        fig (plotly.graph_objects.Figure): plotly figure object
    """
    # plot horizontal line for each bout : bouts {SittingPresent: [(start, end),...], StandingPresent: [(start, end),...]}
    # plot sitting bouts in white and standing bouts in black
    sittingBouts = list(bouts["Sitting"])
    standingBouts = list(bouts["Standing"])
    
    for bout in sittingBouts:
        fig.add_shape(
            dict(
                type="line",
                x0=bout[0],
                y0=0,
                x1=bout[1],
                y1=0,
                line=dict(
                    color="purple",
                    width=100,
                ),
            )
        )
    for bout in standingBouts:
        fig.add_shape(
            dict(
                type="line",
                x0=bout[0],
                y0=0,
                x1=bout[1],
                y1=0,
                line=dict(
                    color="blue",
                    width=100,
                ),
            )
        )
    # add legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', marker=dict(color='purple'), name='Sitting bouts'))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', marker=dict(color='blue'), name='Standing bouts'))
    return fig
  
if __name__ == "__main__":
    fileName = "output//sample.parquet"
    fileNameBase = os.path.basename(fileName).split(".")[0]
    
    # load data and clean it
    print(f"Loding data from {fileName}, cleaning and removing outliers")
    data_frame = analysis.load_from_parquet(fileName)
    data_frame = analysis.check_data(data_frame)
    data_frame = analysis.remove_daily_outliers(data_frame, outlierThreshold=4)
    
    # resample data to 1 minute intervals to compute workdays and remove out of work hours data
    print("Resampling data to 1 minute intervals, computing workdays and removing out of work hours data from the original data")
    resample_data_frame = analysis.resample_data(data_frame, 60)
    workDays = analysis.get_workday(resample_data_frame)
    data_frame = analysis.remove_daily_out_work_hours(data_frame, workDays)
    
    # compute daily threshold, sitting and standing, transitions, presence transitions, and bouts
    print("Computing threshold and transitions")
    data_frame = analysis.compute_daily_threshold(data_frame, minDistance=150)
    data_frame = analysis.compute_sitting_and_standing(data_frame)
    data_frame = analysis.compute_sit_stand_transitions(data_frame)
    data_frame = analysis.compute_present_to_absent_transitions(data_frame)

    print("Computing metrics")
    print("Getting total duration")
    total_duration = analysis.get_data_duration(data_frame)
    print("Getting sitting and standing percentage")
    percStanding = analysis.get_sitting_and_standing_percentage(data_frame)
    print("Getting sit stand transitions")
    transition = analysis.get_sit_stand_transitions(data_frame)
    print("Filtering transitions")
    transition = analysis.filter_transitions(transition, minDuration=120, transitionName1="TransitionToUP", transitionName2="TransitionToDown")
    print("Getting presence transitions")
    presenceTransition = analysis.get_present_to_absent_transitions(data_frame, minDuration=60)
    # presenceTransition =  analysis.filter_transitions(presenceTransition , minDuration=60, transitionName1="AbsentToPresent", transitionName2="PresentToAbsent")
    print("Computing bouts")
    bouts = analysis.compute_bouts( transition, presenceTransition)
    # # bout = analysis.get_bouts(data_frame)
    # data_frame = analysis.resample_data(data_frame, 60)

    timeAtDesk = analysis.get_time_at_desk(data_frame)

    # print(data_frame.head())
    print("Creating plots")
    figures = {}
    fig = plot_data(data_frame, numdays=total_duration.days)
    fig = plot_threshold(data_frame,fig)
    fig = plot_transitions(fig,transition)
    fig = plot_presence_transitions(fig,presenceTransition)
    fig = plot_bouts(fig, bouts)
    figures["time_series"] = fig
    fig = plot_workday(workDays)
    figures["workday"] = fig
    fig = plot_time_at_desk(timeAtDesk)
    figures["time_at_desk"] = fig
    fig = plot_sitting_and_standing_percentage(percStanding)
    figures["sitting_standing"] = fig
    
    for name, fig in figures.items():
        fig.show()
        pio.write_html(fig, f"{fileNameBase}_{name}.html")
    exit()
        
