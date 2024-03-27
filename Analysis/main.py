import os
from datetime import datetime, timedelta
import analysis
from plotly import express as px
from plotly import io as pio

import plotting
from tqdm import tqdm


if __name__ == '__main__':
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
            fig = plotting.plot_data(data_frame, numdays = total_duration.days)
            figures["time_series"] = fig
            fig = plotting.plot_workday(workDays)
            figures["workday"] = fig
            fig = plotting.plot_time_at_desk(timeAtDesk)
            figures["time_at_desk"] = fig
            
            for name, fig in figures.items():
                outFile = os.path.join(output_dir, f"{file_base}_{name}.html")
                pio.write_html(fig, outFile)
    
    