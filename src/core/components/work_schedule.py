import calendar
import logging
import unittest
from typing import List, Tuple

import pandas as pd

from src.core.components.date_time import DateTime
from src.core.global_imports import DAYS_PER_WEEK, HOURS_PER_DAY, MINUTES_PER_HOUR


class WorkScheduleWeek:
    """
    Represents a weekly work schedule.

    Attributes:
        work_schedule (list): Combined daily schedules into a single weekly schedule.
        start_simulation_in_steps (int): Simulation start time in steps.
    """

    def __init__(self, monday, tuesday, wednesday, thursday, friday, saturday, sunday):
        """
        Initialize the weekly work schedule by combining daily schedules and checking for overlaps.
        Instances of WorkScheduleDay representing the schedule for each weekday.

        :param monday: Work schedule for Monday.
        :param tuesday: Work schedule for Tuesday.
        :param wednesday: Work schedule for Wednesday.
        :param thursday: Work schedule for Thursday.
        :param friday: Work schedule for Friday.
        :param saturday: Work schedule for Saturday.
        :param sunday: Work schedule for Sunday.
        """

        self.work_schedule = (monday.get(0) + tuesday.get(1) + wednesday.get(2) + thursday.get(3) + friday.get(4) + saturday.get(5) + sunday.get(6))
        # Determine the simulation start time in steps
        start_day, start_hour, start_minute = DateTime.get(0, False, True)

        self.start_simulation_in_steps = DateTime.map_time_to_steps(start_day - 1, start_hour, start_minute)

        # Check for overlapping shifts within the schedule
        self.find_overlaps()

    def get(self):
        """
        Get the combined weekly schedule and start simulation time in steps.

        :return: Tuple of work schedule and start simulation time in steps.
        """
        return self.work_schedule, self.start_simulation_in_steps

    def print_stats(self, name="unknown"):
        """
        Print statistics about the weekly work schedule.

        :param name: Name of the schedule.
        """
        work_schedule_table = []

        for shift in self.work_schedule:
            day, start_hour, start_minute = steps_in_time(shift[0])
            _, end_hour, end_minute = steps_in_time(shift[1])

            end_minute = str(end_minute).zfill(2)
            start_minute = str(start_minute).zfill(2)
            if end_hour == 0:
                end_hour = 24

            start_time = str(start_hour) + ":" + start_minute
            end_time = str(end_hour) + ":" + end_minute
            capacity = shift[2]

            work_schedule_table.append({
                "weekday": calendar.day_name[day],
                "start": start_time,
                "end": end_time,
                "capacity": capacity,
                "start step": shift[0],
                "end step": shift[1]
            })
        work_schedule_table = pd.DataFrame(work_schedule_table)
        logging.info("Work Schedule Table: %s\n%s\n", name, work_schedule_table)

    def find_overlaps(self):
        """
        Check for overlapping shifts within the schedule.
        """
        shifts = self.work_schedule
        for i in range(len(shifts)):
            for j in range(i + 1, len(shifts)):
                if shifts[i][0] < shifts[j][1] and shifts[i][1] > shifts[j][0]:
                    raise ValueError("There are overlaps in the work schedule!")


class WorkScheduleDay(unittest.TestCase):
    """
    Represents a daily work schedule.

    Attributes:
        work_shift (list): List to store shift details.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize a new instance of WorkScheduleDay, setting up an empty work shift list.
        """
        super(WorkScheduleDay, self).__init__(*args, **kwargs)
        self.work_shift = []    # List to store shift details

    def get(self, day_number: int) -> List[Tuple[int, int, int]]:
        """
        Retrieve shifts for a specific day.

        :param day_number: The day number.
        :return: List of shifts adjusted to the correct day.
        """
        steps_on_day = day_number * DateTime.map_time_to_steps(1)

        # Adjusts each shift to the correct day
        result = [(start + steps_on_day, end + steps_on_day, value) for start, end, value in self.work_shift]
        return result

    # Sets time for a work shift ensuring all values are within valid ranges
    def set_time(self, start_hour: int, start_minute: int, end_hour: int, end_minute: int, capacity: int = 1):
        """
        Set time for a work shift ensuring all values are within valid ranges.

        :param start_hour: Start hour of the shift.
        :param start_minute: Start minute of the shift.
        :param end_hour: End hour of the shift.
        :param end_minute: End minute of the shift.
        :param capacity: Capacity of the shift.
        """
        # Validation for hours and minutes to ensure they are within expected bounds
        self.assertTrue(0 <= start_hour <= 23, "start_hours must be in the range 0-24.")
        self.assertTrue(0 <= end_hour <= 24, "end_hours must be in the range 0-24.")
        self.assertTrue(0 <= start_minute <= 59, "start_minutes must be in the range 0-59.")
        self.assertTrue(0 <= end_minute <= 59, "end_minutes must be in the range 0-59.")
        self.assertTrue(capacity >= 0, "capacity cannot be negative")
        self.assertTrue(not (end_hour == 24 and end_minute != 0), "The day has only 24 hours!")

        # Convert start and end time to steps
        start = DateTime.map_time_to_steps(0, start_hour, start_minute)
        end = DateTime.map_time_to_steps(0, end_hour, end_minute)
        # Append the new shift to the list
        self.work_shift.append((start, end, capacity))

    # Clears all shifts from the work_shift list
    def clear(self):
        self.work_shift = {}


def steps_in_time(step: int) -> Tuple[int, int, int]:
    """
    Convert steps to (weekday, hour, minute).

    :param step: Number of steps.
    :return: Tuple of (weekday, hour, minute).
    """
    # Convert a time duration of one day into simulation steps
    steps_per_day = DateTime.map_time_to_steps(1)
    # Convert a time duration of one hour into simulation steps
    steps_per_hour = DateTime.map_time_to_steps(0, 1)
    # Convert a time duration of one minute into simulation steps
    steps_per_minute = DateTime.map_time_to_steps(0, 0, 1)

    """Calculate the weekday by dividing the total steps by the number of steps per day
    and then taking modulo of the days per week to wrap around the week"""
    weekday = (step // steps_per_day) % DAYS_PER_WEEK
    """Calculate the hour by dividing the total steps by the number of steps per hour
    and taking modulo of the hours per day to wrap around the day"""
    hour = (step // steps_per_hour) % HOURS_PER_DAY
    """Calculate the minute by dividing the total steps by the number of steps per minute
    and taking modulo of the minutes per hour to wrap around the hour"""
    minute = (step // steps_per_minute) % MINUTES_PER_HOUR

    return int(weekday), int(hour), int(minute)


def ask_work_schedule(current_time, work_schedule):
    """
    Determine the status of the work schedule at the current time.

    :param current_time: The current simulation time.
    :param work_schedule: The work schedule to check.
    :return: Tuple of (is_active, time_to_wait, capacity).
    """
    # Initialize a list to track the start of each shift relative to the current week time
    start_of_shifts = []
    # Calculate the total number of steps in a week
    steps_per_week = DateTime.map_time_to_steps(7)
    # Retrieve the work schedule and the simulation start time in steps
    time_to_work, start_simulation_in_steps = work_schedule.get()
    # Adjust the current time by adding the simulation start offset
    current_time += start_simulation_in_steps
    # Calculate the current time's position within the weekly cycle
    step_in_week = current_time % steps_per_week

    # Check each shift to determine if the current time falls within the shift duration
    for shift in time_to_work:
        if shift[0] <= step_in_week < shift[1]:
            return True, 0, shift[2]
        else:
            start_of_shifts.append(shift[0] - step_in_week)

    # Check if all calculated start times are in the past
    if all(element < 0 for element in start_of_shifts):
        time_to_wait = steps_per_week - step_in_week + time_to_work[0][0]
        return False, time_to_wait, None
    else:
        difference = [element for element in start_of_shifts if element >= 0]
        return False, min(difference), None


def load_work_schedule_from_csv(csv_path: str, config: dict = None) -> WorkScheduleWeek:
    """
    Load a weekly work schedule from a CSV file.
    """
    if config:
        df = pd.read_csv(csv_path, **config)
    else:
        df = pd.read_csv(csv_path)

    # Create a WorkScheduleDay instance for each weekday
    days = {
        "Monday": WorkScheduleDay(),
        "Tuesday": WorkScheduleDay(),
        "Wednesday": WorkScheduleDay(),
        "Thursday": WorkScheduleDay(),
        "Friday": WorkScheduleDay(),
        "Saturday": WorkScheduleDay(),
        "Sunday": WorkScheduleDay()
    }
    for _, row in df.iterrows():
        day = row['day']
        start_hour = int(row['start_hour'])
        start_minute = int(row['start_minute'])
        end_hour = int(row['end_hour'])
        end_minute = int(row['end_minute'])
        capacity = int(row['capacity'])
        days[day].set_time(start_hour, start_minute, end_hour, end_minute, capacity)
    week = WorkScheduleWeek(
        days["Monday"],
        days["Tuesday"],
        days["Wednesday"],
        days["Thursday"],
        days["Friday"],
        days["Saturday"],
        days["Sunday"]
    )
    return week
