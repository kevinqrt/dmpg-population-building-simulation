from typing import Union, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.integrate import odeint

from src.core.components.date_time import DateTime


class Oven:
    """
    Represents an oven with the ability to heat a workpiece and control temperature.

    Attributes:
        temperature_current_outside (float): Current outside temperature.
        temperature_initiale_setpoint (float): Initial setpoint temperature.
        temperature_current_setpoint (float): Current setpoint temperature.
        number_of_calculates_between_two_time_stamps (int): Number of calculations between two time stamps.
        current_values (list): Initial temperatures of the workpiece and oven.
        proportionality_constant_temperature_workpiece (float): Proportionality constant for the workpiece temperature.
        proportionality_constant_temperature_oven (float): Proportionality constant for the oven temperature.
        proportionality_constant_door (float): Proportionality constant for the door.
        temperature_history_workpiece (list): History of workpiece temperature.
        temperature_history_oven (list): History of oven temperature.
        temperature_history_setpoint (list): History of setpoint temperature.
        list_with_timestamps (list): List of timestamps.
        list_with_timestamps_in_steps (list): List of timestamps in steps.
        last_step (int): The last step in the simulation.
        show_diagram (bool): Flag to indicate if the diagram should be shown.
        door_status (int): Status of the door (0 for closed, 1 for open).
        door_status_history (list): History of door statuses.
    """

    def __init__(self, temperature_initiale_workpiece: Union[int, float] = 20,
                 temperature_initiale_oven: Union[int, float] = 20,
                 temperature_initiale_setpoint: Union[int, float] = 200,
                 temperature_current_outside: Union[int, float] = 20,
                 number_of_calculate_between_two_timestamps: Union[int, float] = 10):
        """
        Initialize an Oven instance with given parameters.

        :param temperature_initiale_workpiece: Initial temperature of the workpiece.
        :param temperature_initiale_oven: Initial temperature of the oven.
        :param temperature_initiale_setpoint: Initial setpoint temperature.
        :param temperature_current_outside: Current outside temperature.
        :param number_of_calculate_between_two_timestamps: Number of calculations between two time stamps.
        """

        self.temperature_current_outside = temperature_current_outside
        self.temperature_initiale_setpoint = temperature_initiale_setpoint
        self.temperature_current_setpoint = temperature_initiale_setpoint
        self.number_of_calculates_between_two_time_stamps = number_of_calculate_between_two_timestamps
        self.current_values = [temperature_initiale_workpiece, temperature_initiale_oven]

        self.proportionality_constant_temperature_workpiece = 0.2
        self.proportionality_constant_temperature_oven = 0.3
        self.proportionality_constant_door = 0.5

        self.temperature_history_workpiece = []
        self.temperature_history_oven = []
        self.temperature_history_setpoint = []

        self.list_with_timestamps = []
        self.list_with_timestamps_in_steps = []

        self.last_step = 0
        self.show_diagram = False
        self.door_status = 0
        self.door_status_history = []

    def model(self, current_values: List[float], t: float, proportionality_constant_workpiece: float,
              proportionality_constant_oven: float, proportionality_constant_door: float):
        """
        Model the temperature changes in the oven and workpiece.

        :param current_values: Current temperature values for the workpiece and oven.
        :param t: Time (required by odeint, even if not used).
        :param proportionality_constant_workpiece: Proportionality constant for the workpiece.
        :param proportionality_constant_oven: Proportionality constant for the oven.
        :param proportionality_constant_door: Proportionality constant for the door.
        :return: List of temperature changes for the workpiece and oven.
        """

        temperature_current_workpiece, temperature_current_oven = current_values

        d_temperature_workpiece_dt = (-proportionality_constant_workpiece * (temperature_current_workpiece - temperature_current_oven))
        d_temperature_oven_dt = (-proportionality_constant_oven * (temperature_current_oven - self.temperature_current_setpoint) - self.door_status * proportionality_constant_door * (temperature_current_oven - self.temperature_current_outside))

        return [d_temperature_workpiece_dt, d_temperature_oven_dt]

    def calculate_oven(self, current_step):
        """
        Calculate the temperature changes in the oven over a given time step.

        :param current_step: The current step in the simulation.
        """

        time_range = np.linspace(self.last_step, current_step,
                                 self.number_of_calculates_between_two_time_stamps)

        # self.list_with_timestamps_in_steps.append(round(time_range[-1], 2))
        self.list_with_timestamps_in_steps.extend(time_range)
        # self.door_status_history.append(self.door_status*10)
        self.door_status_history.extend([self.door_status * 10] * self.number_of_calculates_between_two_time_stamps)
        self.temperature_history_setpoint.extend([self.temperature_current_setpoint] * self.number_of_calculates_between_two_time_stamps)

        solution = odeint(self.model,
                          self.current_values,
                          time_range,
                          args=(self.proportionality_constant_temperature_workpiece,
                                self.proportionality_constant_temperature_oven,
                                self.proportionality_constant_door))

        temperature_current_workpiece = solution[:, 0]
        temperature_current_oven = solution[:, 1]
        self.current_values = [temperature_current_workpiece[-1], temperature_current_oven[-1]]

        # temperature_current_setpoint = solution[:, 2]

        # self.temperature_history_workpiece.append(temperature_current_workpiece[-1])
        # self.temperature_history_oven.append(temperature_current_oven[-1])
        self.temperature_history_workpiece.extend(temperature_current_workpiece)
        self.temperature_history_oven.extend(temperature_current_oven)
        # self.temperature_history_setpoint.append(self.temperature_initiale_setpoint)

        self.last_step = current_step

        if current_step > 120 and self.show_diagram is True:
            self.show_infos()
            self.show_diagram = False

    def calculate_time_to_required_temperature(self) -> Union[int, float]:
        """
        Calculate the time required for the oven to heat up to the required temperature using the differential model.
        This provides a more accurate calculation of the time required to reach the desired temperature.

        :return: time_to_heat (float): Time required to reach the desired temperature.
        """
        current_temp = self.current_values[1]
        target_temp = self.temperature_initiale_setpoint

        if current_temp >= (target_temp - 15):
            return 0  # Already close enough to the required temperature

        # Define the simulation time range and a reasonable step size
        max_simulation_time = 10000  # Large enough time to allow heating
        time_step = 0.1
        time_range = np.arange(0, max_simulation_time, time_step)

        # Simulate the oven heating process over time using odeint
        solution = odeint(self.model,
                          self.current_values,
                          time_range,
                          args=(self.proportionality_constant_temperature_workpiece,
                                self.proportionality_constant_temperature_oven,
                                self.proportionality_constant_door))

        # Find the first time step where the oven reaches the required temperature
        temperature_oven_over_time = solution[:, 1]
        for i, temperature in enumerate(temperature_oven_over_time):
            if temperature >= (target_temp - 15):
                return time_range[i]  # Return the time at which the target temperature is reached

        return max_simulation_time  # If never reaches the target within the simulation, return max time

    def show_infos(self):
        """
        Display the temperature changes in the oven and workpiece over time.
        """

        plt.xlabel('Time (minute)')
        plt.ylabel('Temperature (°C)')
        plt.title('Temperatures Oven')
        plt.plot(self.list_with_timestamps_in_steps, self.temperature_history_setpoint, label='Temperature of Setpoint')
        plt.plot(self.list_with_timestamps_in_steps, self.temperature_history_workpiece, label='Temperature of Workpiece')
        plt.plot(self.list_with_timestamps_in_steps, self.temperature_history_oven, label='Temperature of Oven')
        plt.plot(self.list_with_timestamps_in_steps, self.door_status_history, label='Door status')

        plt.legend(loc='lower right')
        plt.grid(True)
        plt.show()

        for timestamp_in_step in self.list_with_timestamps_in_steps:
            timestamp = DateTime.get(round(timestamp_in_step, 1), True)
            self.list_with_timestamps.append(timestamp)

        data = {'Date': self.list_with_timestamps,
                'step': self.list_with_timestamps_in_steps,
                'Temperature of Workpiece': self.temperature_history_workpiece,
                'Temperature of Oven': self.temperature_history_oven,
                # 'Temperature of Setpoint': self.temperature_history_setpoint
                }

        dataframe_solution_dgl = pd.DataFrame(data)
        dataframe_solution_dgl['Temperature of Oven'] = dataframe_solution_dgl['Temperature of Oven'].round(2)
        dataframe_solution_dgl['Temperature of Workpiece'] = dataframe_solution_dgl['Temperature of Workpiece'].round(2)
        pd.set_option('display.width', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.colheader_justify', 'center')
        # logging.info("Temperatures Oven \n%s\n", dataframe_solution_dgl)

    def ask_required_temperature(self):
        """
        Check if the oven temperature has reached the setpoint temperature.

        :return: True if the oven temperature is close to the setpoint, otherwise False.
        """

        if round(self.current_values[1]) >= (self.temperature_initiale_setpoint - 15):
            return True
        else:
            return False

    def update_oven(self, heating_status: bool = True, door_status: bool = False):
        """
        Update the setpoint temperature and door status of the oven.

        :param heating_status: True if the heating is on, otherwise False.
        :param door_status: True if the door is open, otherwise False.
        """

        if heating_status:
            self.temperature_current_setpoint = self.temperature_initiale_setpoint
        else:
            self.temperature_current_setpoint = self.temperature_current_outside

        if door_status:
            self.door_status = 1  # open
        else:
            self.door_status = 0  # close
