import os
from datetime import datetime, timedelta
import analysis
from plotly import express as px
from plotly import io as pio

import plotting
from tqdm import tqdm
from tkinter import filedialog
import tkinter as tk


if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    # input_dir = "C:\\Users\\LocalSK\\Downloads\\DPS_Merged"
    input_dir = filedialog.askdirectory(title="Select the folder containing the Standup data")
    if not input_dir:
        print("No folder selected. Exiting.")
        exit()
    # output_dir = "C:\\Users\\LocalSK\\Downloads\\DPS_Merged\\results"
    output_dir = filedialog.askdirectory(title="Select the output folder")
    if not output_dir:
        print("No output folder selected. Exiting.")
        exit()
    # check if the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    completeFileList = [os.path.join(path, name) for path, subdirs, files in os.walk(input_dir) for name in files if name.endswith(".parquet")]
    

    for file in tqdm(completeFileList, desc="Processing files", dynamic_ncols=True):
        print(f"Loading {file}")
        data_frame = analysis.load_from_parquet(file)
        data_frame = analysis.check_data(data_frame)
        
        file_base = os.path.basename(file) # get the file name without the path
        # get file name without extension
        file_base = os.path.splitext(file_base)[0]
        total_duration = analysis.get_data_duration(data_frame)
        if total_duration > timedelta(hours=24):
            print(f"Processing {file_base} with duration {total_duration}")
            data_frame = analysis.remove_daily_outliers(data_frame,outlierThreshold=4)
            resampled_data_frame = analysis.resample_data(data_frame, 60)
            workDays = analysis.get_workday(resampled_data_frame)
            data_frame = analysis.remove_daily_out_work_hours(data_frame, workDays)
            print(f"Computing threshold and transitions for {file_base}")
            data_frame = analysis.compute_daily_threshold(data_frame, minDistance=150)
            data_frame = analysis.compute_sitting_and_standing(data_frame)
            data_frame = analysis.compute_sit_stand_transitions(data_frame)
            data_frame = analysis.compute_present_to_absent_transitions(data_frame)

            print(f"Computing metrics for {file_base}")
            percStanding = analysis.get_sitting_and_standing_percentage(data_frame)
            transition = analysis.get_sit_stand_transitions(data_frame)
            transition = analysis.filter_transitions(transition, minDuration=120, transitionName1="TransitionToUP", transitionName2="TransitionToDown")
            presenceTransition = analysis.get_present_to_absent_transitions(data_frame, minDuration=60)
            bouts = analysis.compute_bouts(transition, presenceTransition)

            dailyTransitions = analysis.get_num_of_daily_transition(transition)
            timeAtDesk = analysis.get_time_at_desk(data_frame)
            
            data_frame = analysis.resample_data(data_frame, 60)
            print(f"Exporting summary for {file_base}")
            analysis.noahSummaryExport(output_dir, file_base, dailyTransitions, percStanding, workDays, bouts)
            
            print(f"Plotting figures for {file_base}")
            figures = {}
            fig = plotting.plot_data(data_frame, numdays=total_duration.days)
            fig = plotting.plot_threshold(data_frame,fig)
            fig = plotting.plot_transitions(fig,transition)
            fig = plotting.plot_presence_transitions(fig,presenceTransition)
            fig = plotting.plot_bouts(fig, bouts)
            figures["time_series"] = fig

            fig = plotting.plot_workday(workDays)
            figures["workday"] = fig
            fig = plotting.plot_time_at_desk(timeAtDesk)
            figures["time_at_desk"] = fig
            fig = plotting.plot_sitting_and_standing_percentage(percStanding)
            figures["sitting_standing"] = fig

            print(f"Saving figures for {file_base}")
            for name, fig in tqdm(figures.items(), desc="Saving figures", dynamic_ncols=True):
                plot_output_dir = os.path.join(output_dir, name)
                # create a directory for each name if it does not exist
                if not os.path.exists(plot_output_dir):
                    os.makedirs(plot_output_dir)
                outFile = os.path.join(plot_output_dir, f"{name}_{file_base}.html")
                pio.write_html(fig, outFile)
    
        