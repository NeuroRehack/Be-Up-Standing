import os
from datetime import datetime, timedelta
import analysis
from plotly import express as px
from plotly import io as pio

import plotting
from tqdm import tqdm


if __name__ == '__main__':
    input_dir = "C:\\DPS_Out_2"
    output_dir = "C:\\DPS_Out_2\\results"
    completeFileList = [os.path.join(path, name) for path, subdirs, files in os.walk(input_dir) for name in files if name.endswith(".parquet")]
    

    for file in tqdm(completeFileList):
        data_frame = analysis.load_from_parquet(file)
        data_frame = analysis.check_data(data_frame)
        
        file_base = os.path.basename(file) # get the file name without the path
        # get file name without extension
        file_base = os.path.splitext(file_base)[0]
        total_duration = analysis.get_data_duration(data_frame)
        if total_duration > timedelta(hours=24):
            data_frame = analysis.remove_daily_outliers(data_frame,outlierThreshold=4)
            resampled_data_frame = analysis.resample_data(data_frame, 60)
            workDays = analysis.get_workday(resampled_data_frame)
            data_frame = analysis.remove_daily_out_work_hours(data_frame, workDays)
            
            data_frame = analysis.compute_daily_threshold(data_frame, minDistance=150)
            data_frame = analysis.compute_sitting_and_standing(data_frame)
            data_frame = analysis.compute_sit_stand_transitions(data_frame)

            percStanding = analysis.get_sitting_and_standing_percentage(data_frame)
            transition = analysis.get_sit_stand_transitions(data_frame)
            transition = analysis.filter_transitions(transition, minDuration=120)
            dailyTransitions = analysis.get_num_of_daily_transition(transition)
            
            data_frame = analysis.resample_data(data_frame, 60)
            # timeAtDesk = analysis.get_time_at_desk(data_frame)
            
            analysis.noahSummaryExport(output_dir, file_base, dailyTransitions, percStanding, workDays)
            
            figures = {}
            fig = plotting.plot_data(data_frame, numdays=total_duration.days)
            fig = plotting.plot_threshold(data_frame,fig)
            fig = plotting.plot_transitions(fig,transition)
            figures["time_series"] = fig
            # fig = plotting.plot_workday(workDays)
            # figures["workday"] = fig
            # # fig = plotting.plot_time_at_desk(timeAtDesk)
            # # figures["time_at_desk"] = fig
            # fig = plotting.plot_sitting_and_standing_percentage(percStanding)
            # figures["sitting_standing"] = fig
        
            
            for name, fig in figures.items():
                plot_output_dir = os.path.join(output_dir, name)
                # create a directory for each name if it does not exist
                if not os.path.exists(plot_output_dir):
                    os.makedirs(plot_output_dir)
                outFile = os.path.join(plot_output_dir, f"{name}_{file_base}.html")
                pio.write_html(fig, outFile)
    
        