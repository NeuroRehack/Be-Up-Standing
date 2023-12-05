"""
File: dash_data_receive_server.py
Description: This script implements a dashboard to display the sensor data received from the device. It provides a graphical user interface (GUI) using Dash for users to view the sensor data.
Author: [Sami Kaab]
Date: [2023-07-03]
"""
import requests
import dash
from dash import dcc
from dash import html
from dash.dependencies import Output, Input
from collections import deque
import datetime
import waitress
import logging

logging.getLogger("waitress.queue").setLevel(logging.WARNING)


"""
This class implements a dashboard to display the sensor data received from the device. It provides a graphical user interface (GUI) using Dash for users to view the sensor data.
"""
class SensorDataApp:
    def __init__(self, hostname = None):
        self.hostname = hostname
        self.url = f'http://{self.hostname}:5000/sensor-data'
        self.sensor_data_queue = deque(maxlen=100)
        self.app = dash.Dash(__name__)
        self.server = None
        self.app.layout = html.Div(
            id='light-theme-container',
            style={'background-color': 'white', 'color': 'black', 'padding': '50px'}
        )

        self.app.layout.children = [
            # html.H1("Be Up Standing", style={'textAlign': 'center', 'color': 'black', 'font-size': '60px', 'font-weight': 'bold'}),
            html.Div(
                id="sensor-id",
                style={
                    'border': '1px solid black',
                    'padding': '10px',
                    'font-weight': 'bold',
                    'white-space': 'pre-line',
                    'max-width': '300px',   # Set the maximum width of the box
                    'max-height': '200px',  # Set the maximum height of the box
                    'min-width': '150px',   # Set the minimum width of the box
                    'min-height': '100px',  # Set the minimum height of the box
                    'margin-right': '20px',  # Set a margin to create space between the boxes
                    'display': 'inline-block',  # Display the box as an inline block
                    'font-size': '20px',  # set font size to 20px

                },
            ),
            html.Div(
                id="latest-values",
                style={
                    'border': '1px solid black',
                    'padding': '10px',
                    'font-weight': 'bold',
                    'white-space': 'pre-line',
                    'max-width': '300px',   # Set the maximum width of the box
                    'max-height': '200px',  # Set the maximum height of the box
                    'min-width': '150px',   # Set the minimum width of the box
                    'min-height': '100px',  # Set the minimum height of the box
                    'display': 'inline-block',  # Display the box as an inline block
                    'vertical-align': 'top',  # Align the box with the top of the "sensor-id" box
                    'font-size': '20px',  # set font size to 20px

                },
            ),
            html.Div(
                dcc.Slider(
                    id='window-slider',
                    min=0,
                    max=110,
                    step=10,
                    value=100,
                    marks={str(i): str(i) for i in range(0, 101, 5)},
                    included=False,
                    className='light-theme-control'
                ),
                style={'color': 'black'}
            ),
            dcc.Graph(id="live-graph-distance", animate=True),
            dcc.Graph(id="live-graph-human-presence", animate=True),
            dcc.Interval(id="graph-update", interval=2000, n_intervals=0),
        ]

        self.app.callback(
            Output("sensor-id", "children"),
            Output("live-graph-distance", "figure"),
            Output("live-graph-human-presence", "figure"),
            Output("latest-values", "children"),
            [Input("graph-update", "n_intervals"), Input("window-slider", "value")]
        )(self.update_data)
        
        

    def update_data(self, n, window):
        """ This function is called periodically to update the sensor data displayed on the dashboard. It is called every second by the dcc.Interval component. It is also called when the user changes the window size using the slider.
            Args:
                n (int): The number of times the dcc.Interval component has called this function.
                window (int): The number of data points to display on the graph.
            Returns:
                sensor_id (str): The ID of the sensor.
                distance_data (dict): The data to display on the distance graph.
                human_presence_data (dict): The data to display on the human presence graph.
                latest_values (str): The latest sensor values.
        """
        self.url = f'http://{self.hostname}:5000/sensor-data'

        try:
            response = requests.get(self.url)
            # Process the response here
            
            if response.status_code == 200:
                sensor_data = response.json()
                if sensor_data['message'] == "ok":
                    self.sensor_data_queue.append(sensor_data)
                sensor_data = self.sensor_data_queue[-1]
                latest_values = f"Time:{datetime.datetime.strptime(sensor_data['datetime'], '%a, %d %b %Y %H:%M:%S %Z')}\nDistance : {sensor_data['distance']/1000} m\nSomeone present:{'Yes' if sensor_data['human_presence'] == 1 else 'No'}\n Battery Level: {sensor_data['battery_level']}%"
                sensor_id = self.sensor_data_queue[-1]['id']
                sensor_period = int(self.sensor_data_queue[-1]['fs'])
            else:
                sensor_id = "Unknown"
                latest_values = "Latest Values: Unknown"
                sensor_period = 1
            y_distance = [data['distance']/1000 for data in list(self.sensor_data_queue)[-window:]]
            t = [datetime.datetime.strptime(data['datetime'], "%a, %d %b %Y %H:%M:%S %Z") for data in list(self.sensor_data_queue)[-window:]]
            distance_data = {
                'x': t,
                'y': y_distance,
                'type': 'scatter',
                'mode': 'lines+markers',
                'marker': {'color': 'blue'},
                'name': 'Distance'
            }
            layout_distance = {
                'title': {
                    'text': 'Distance Sensor',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                'xaxis': {'title': 'Time', 'range': [t[0], t[-1] + datetime.timedelta(seconds=sensor_period)],'gridcolor': 'black'},
                'yaxis': {'title': 'Distance (m)', 'range': [0.9*min(y_distance), 1.1*max(y_distance)],'gridcolor': 'black'},
                'paper_bgcolor': 'white',
                'plot_bgcolor': 'white',
                'font': {'color': 'black'}
            }

            y_presence = [data['human_presence']*2-1 for data in list(self.sensor_data_queue)[-window:]]
            presence_values = ['Present' if presence == 1 else 'Not Present' for presence in y_presence]

            presence_data = {
                'x': t,
                'y': y_presence,
                'type': 'bar',
                'marker': {
                    'color': ['green' if presence == 1 else 'red' for presence in y_presence],
                    'line': {'color': 'black', 'width': 1}
                },
                'name': 'Human Presence',
                'text': presence_values,
                'textposition': 'auto'
            }

            layout_presence = {
                'title': {
                    'text': 'Human Presence Detector',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                'xaxis': {'title': 'Time', 'range': [t[0], t[-1] + datetime.timedelta(seconds=sensor_period)]},
                'yaxis': {'visible': False},
                'paper_bgcolor': 'white',
                'plot_bgcolor': 'white',
                'font': {'color': 'black'}
            }

            config_info = f"""Sensor ID: {sensor_id}
                Sampling Period: {self.sensor_data_queue[-1]['fs']}s
                Writing Period: {self.sensor_data_queue[-1]['wp']}s 
                New File Period: {self.sensor_data_queue[-1]['nfp']}s
                Upload Period: {self.sensor_data_queue[-1]['ufs']}s
                Wake At: {self.sensor_data_queue[-1]['wa']}
                Sleep At: {self.sensor_data_queue[-1]['sa']}"""
            return config_info, {'data': [distance_data], 'layout': layout_distance}, {'data': [presence_data], 'layout': layout_presence}, latest_values
        except Exception as e:
            print(e)
            # Handle the connection error
            config_info = ""
            distance_data = {}
            presence_data = {}
            layout_distance = {}
            layout_presence = {}
            latest_values = ""

            return config_info, {'data': [distance_data], 'layout': layout_distance}, {'data': [presence_data], 'layout': layout_presence}, latest_values

        
    def run(self):
        # self.app.run_server()
        self.server = waitress.serve(self.app.server, host='127.0.0.1', port=8050)


if __name__ == '__main__':
    sensor_app = SensorDataApp(hostname="standup-a17e.local")
    sensor_app.run()
