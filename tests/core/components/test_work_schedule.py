import unittest
import tempfile
import os
from datetime import datetime
from unittest.mock import patch

from src.core.components.date_time import DateTime
from src.core.components.work_schedule import (
    WorkScheduleDay, WorkScheduleWeek, ask_work_schedule,
    steps_in_time, load_work_schedule_from_csv
)


class TestWorkScheduleDay(unittest.TestCase):
    """Test cases for the WorkScheduleDay class."""

    def setUp(self):
        """Set up baseline for DateTime and initialize WorkScheduleDay."""
        DateTime.set(datetime(2024, 1, 1, 0, 0, 0))
        self.work_day = WorkScheduleDay()

    def test_initialization(self):
        """Test WorkScheduleDay initialization."""
        work_day = WorkScheduleDay()
        self.assertEqual(work_day.work_shift, [])

        self.assertIsInstance(work_day, unittest.TestCase)

    def test_set_time_valid_basic(self):
        """Test valid shift times are added correctly."""
        self.work_day.set_time(8, 0, 17, 0)
        shifts = self.work_day.get(0)  # Get shifts for Monday (day 0)
        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0][2], 1)  # Default capacity should be 1

    def test_set_time_valid_with_capacity(self):
        """Test setting time with custom capacity."""
        self.work_day.set_time(9, 30, 15, 45, capacity=3)
        shifts = self.work_day.get(0)
        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0][2], 3)  # Custom capacity

    def test_set_time_multiple_shifts(self):
        """Test adding multiple shifts to the same day."""
        self.work_day.set_time(8, 0, 12, 0, capacity=2)  # Morning shift
        self.work_day.set_time(13, 0, 17, 0, capacity=1)  # Afternoon shift
        shifts = self.work_day.get(0)
        self.assertEqual(len(shifts), 2)
        self.assertEqual(shifts[0][2], 2)  # Morning capacity
        self.assertEqual(shifts[1][2], 1)  # Afternoon capacity

    def test_set_time_edge_case_24_hour(self):
        """Test setting time at 24:00 (end of day)."""
        self.work_day.set_time(0, 0, 24, 0, capacity=1)
        shifts = self.work_day.get(0)
        self.assertEqual(len(shifts), 1)

    def test_set_time_edge_case_minutes(self):
        """Test setting time with various minute values."""
        self.work_day.set_time(8, 15, 17, 45, capacity=2)
        shifts = self.work_day.get(0)
        self.assertEqual(len(shifts), 1)

    def test_set_time_zero_capacity(self):
        """Test setting time with zero capacity."""
        self.work_day.set_time(9, 0, 17, 0, capacity=0)
        shifts = self.work_day.get(0)
        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0][2], 0)

    def test_set_time_invalid_start_hour_negative(self):
        """Test invalid start hour (negative)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(-1, 0, 17, 0)

    def test_set_time_invalid_start_hour_too_high(self):
        """Test invalid start hour (> 23)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(25, 0, 17, 0)

    def test_set_time_invalid_end_hour_negative(self):
        """Test invalid end hour (negative)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 0, -1, 0)

    def test_set_time_invalid_end_hour_too_high(self):
        """Test invalid end hour (> 24)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 0, 25, 0)

    def test_set_time_invalid_start_minute_negative(self):
        """Test invalid start minute (negative)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, -1, 17, 0)

    def test_set_time_invalid_start_minute_too_high(self):
        """Test invalid start minute (> 59)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 60, 17, 0)

    def test_set_time_invalid_end_minute_negative(self):
        """Test invalid end minute (negative)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 0, 17, -1)

    def test_set_time_invalid_end_minute_too_high(self):
        """Test invalid end minute (> 59)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 0, 17, 60)

    def test_set_time_invalid_negative_capacity(self):
        """Test invalid capacity (negative)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 0, 17, 0, capacity=-1)

    def test_set_time_invalid_24_hour_with_minutes(self):
        """Test invalid 24:XX (24 hours with non-zero minutes)."""
        with self.assertRaises(AssertionError):
            self.work_day.set_time(8, 0, 24, 30)

    def test_get_different_days(self):
        """Test getting shifts for different days of the week."""
        self.work_day.set_time(9, 0, 17, 0, capacity=2)

        # Test different days
        for day in range(7):
            shifts = self.work_day.get(day)
            self.assertEqual(len(shifts), 1)
            self.assertEqual(shifts[0][2], 2)  # Capacity should be same

            # The start and end times should be adjusted by day offset
            actual_start = shifts[0][0]

            # Verify the day offset is correctly applied
            if day > 0:
                self.assertGreater(actual_start, DateTime.map_time_to_steps(0, 9, 0))

    def test_clear(self):
        """Test clear method resets shifts."""
        self.work_day.set_time(8, 0, 17, 0)
        self.work_day.set_time(18, 0, 22, 0)
        self.assertEqual(len(self.work_day.work_shift), 2)

        self.work_day.clear()
        # According to the implementation, clear() sets work_shift to {}
        self.assertEqual(self.work_day.work_shift, {})


class TestWorkScheduleWeek(unittest.TestCase):
    """Test cases for the WorkScheduleWeek class."""

    def setUp(self):
        DateTime.set(datetime(2024, 1, 1, 0, 0, 0))

        # Create different day schedules
        self.monday = WorkScheduleDay()
        self.monday.set_time(9, 0, 17, 0, capacity=2)

        self.tuesday = WorkScheduleDay()
        self.tuesday.set_time(10, 0, 18, 0, capacity=3)

        self.wednesday = WorkScheduleDay()
        self.wednesday.set_time(8, 0, 16, 0, capacity=1)

        self.empty_day = WorkScheduleDay()

    def test_initialization_no_overlap(self):
        """Test week initialization without overlapping shifts."""
        schedule_week = WorkScheduleWeek(
            self.monday, self.tuesday, self.wednesday, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )
        self.assertEqual(len(schedule_week.work_schedule), 3)

    def test_initialization_all_empty_days(self):
        """Test week initialization with all empty days."""
        schedule_week = WorkScheduleWeek(
            self.empty_day, self.empty_day, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )
        self.assertEqual(len(schedule_week.work_schedule), 0)

    def test_initialization_single_day_schedule(self):
        """Test week initialization with only one day having a schedule."""
        schedule_week = WorkScheduleWeek(
            self.monday, self.empty_day, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )
        self.assertEqual(len(schedule_week.work_schedule), 1)

    def test_find_overlaps_same_day(self):
        """Test that overlapping shifts on the same day raise an error."""
        overlapping_monday = WorkScheduleDay()
        overlapping_monday.set_time(9, 0, 17, 0)  # 9 AM - 5 PM
        overlapping_monday.set_time(16, 0, 20, 0)  # 4 PM - 8 PM (overlaps with first)

        with self.assertRaises(ValueError) as context:
            WorkScheduleWeek(
                overlapping_monday, self.empty_day, self.empty_day,
                self.empty_day, self.empty_day, self.empty_day, self.empty_day
            )
        self.assertIn("overlaps", str(context.exception))

    def test_find_overlaps_adjacent_shifts(self):
        """Test that adjacent (non-overlapping) shifts work correctly."""
        adjacent_day = WorkScheduleDay()
        adjacent_day.set_time(8, 0, 12, 0)   # 8 AM - 12 PM
        adjacent_day.set_time(12, 0, 16, 0)  # 12 PM - 4 PM (touching but not overlapping)

        # This should NOT raise an error
        schedule_week = WorkScheduleWeek(
            adjacent_day, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day, self.empty_day
        )
        self.assertEqual(len(schedule_week.work_schedule), 2)

    def test_find_overlaps_cross_day_boundary(self):
        """Test shifts that might cross day boundaries."""
        late_shift = WorkScheduleDay()
        late_shift.set_time(22, 0, 24, 0)  # 10 PM - 12 AM

        early_shift = WorkScheduleDay()
        early_shift.set_time(0, 0, 6, 0)   # 12 AM - 6 AM

        # These are on different days so should not overlap
        schedule_week = WorkScheduleWeek(
            late_shift, early_shift, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )
        self.assertEqual(len(schedule_week.work_schedule), 2)

    def test_get_start_simulation_steps_calculation(self):
        """Test that start simulation steps are calculated correctly."""
        # Set a specific start time
        DateTime.set(datetime(2024, 4, 1, 10, 30, 0))  # Monday 10:30 AM

        schedule_week = WorkScheduleWeek(
            self.monday, self.empty_day, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )
        schedule, start_steps = schedule_week.get()

        # start_steps should reflect the current time
        self.assertGreater(start_steps, 0)

    @patch('logging.info')
    def test_print_stats(self, mock_logging):
        """Test the print_stats method."""
        schedule_week = WorkScheduleWeek(
            self.monday, self.tuesday, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )

        # Test with default name
        schedule_week.print_stats()
        mock_logging.assert_called()

        # Test with custom name
        mock_logging.reset_mock()
        schedule_week.print_stats("Custom Schedule")
        mock_logging.assert_called()

        # Verify the logged content contains expected information
        logged_calls = [str(call) for call in mock_logging.call_args_list]
        logged_content = ''.join(logged_calls)
        self.assertIn("Custom Schedule", logged_content)

    @patch('logging.info')
    def test_print_stats_with_complex_schedule(self, mock_logging):
        """Test print_stats with a more complex schedule."""
        complex_day = WorkScheduleDay()
        complex_day.set_time(6, 30, 14, 15, capacity=3)  # Morning shift
        complex_day.set_time(14, 30, 22, 45, capacity=2)  # Evening shift

        schedule_week = WorkScheduleWeek(
            complex_day, self.empty_day, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )

        schedule_week.print_stats("Complex")

        # Verify logging was called
        self.assertTrue(mock_logging.called)

    def test_print_stats_empty_schedule(self):
        """Test print_stats with empty schedule."""
        empty_week = WorkScheduleWeek(
            self.empty_day, self.empty_day, self.empty_day, self.empty_day,
            self.empty_day, self.empty_day, self.empty_day
        )

        # Should not raise an error even with empty schedule
        with patch('logging.info') as mock_logging:
            empty_week.print_stats("Empty")
            mock_logging.assert_called()


class TestStepsInTime(unittest.TestCase):
    """Test cases for the steps_in_time function."""

    def setUp(self):
        DateTime.set(datetime(2024, 1, 1, 0, 0, 0))  # Monday

    def test_steps_in_time_zero(self):
        """Test steps_in_time with zero steps."""
        weekday, hour, minute = steps_in_time(0)
        self.assertEqual(weekday, 0)  # Monday
        self.assertEqual(hour, 0)
        self.assertEqual(minute, 0)

    def test_steps_in_time_one_hour(self):
        """Test steps_in_time with one hour worth of steps."""
        one_hour_steps = DateTime.map_time_to_steps(0, 1, 0)
        weekday, hour, minute = steps_in_time(one_hour_steps)
        self.assertEqual(weekday, 0)  # Still Monday
        self.assertEqual(hour, 1)
        self.assertEqual(minute, 0)

    def test_steps_in_time_one_day(self):
        """Test steps_in_time with one day worth of steps."""
        one_day_steps = DateTime.map_time_to_steps(1, 0, 0)
        weekday, hour, minute = steps_in_time(one_day_steps)
        self.assertEqual(weekday, 1)  # Tuesday
        self.assertEqual(hour, 0)
        self.assertEqual(minute, 0)

    def test_steps_in_time_one_week(self):
        """Test steps_in_time with one week worth of steps."""
        one_week_steps = DateTime.map_time_to_steps(7, 0, 0)
        weekday, hour, minute = steps_in_time(one_week_steps)
        self.assertEqual(weekday, 0)  # Wraps back to Monday
        self.assertEqual(hour, 0)
        self.assertEqual(minute, 0)

    def test_steps_in_time_complex_time(self):
        """Test steps_in_time with a complex time."""
        # 2 days, 15 hours, 45 minutes
        complex_steps = DateTime.map_time_to_steps(2, 15, 45)
        weekday, hour, minute = steps_in_time(complex_steps)
        self.assertEqual(weekday, 2)  # Wednesday
        self.assertEqual(hour, 15)   # 3 PM
        self.assertEqual(minute, 45)

    def test_steps_in_time_week_wrap_around(self):
        """Test steps_in_time with week wrap-around scenarios."""
        # 10 days should wrap around (10 % 7 = 3, so Wednesday)
        ten_days_steps = DateTime.map_time_to_steps(10, 0, 0)
        weekday, hour, minute = steps_in_time(ten_days_steps)
        self.assertEqual(weekday, 3)  # Wednesday

    def test_steps_in_time_large_numbers(self):
        """Test steps_in_time with large step numbers."""
        # Test with a very large number of steps
        large_steps = DateTime.map_time_to_steps(100, 23, 59)
        weekday, hour, minute = steps_in_time(large_steps)

        # Should still wrap around correctly
        self.assertIn(weekday, range(7))  # Valid weekday
        self.assertIn(hour, range(24))    # Valid hour
        self.assertIn(minute, range(60))  # Valid minute

    def test_steps_in_time_return_types(self):
        """Test that steps_in_time returns integers."""
        weekday, hour, minute = steps_in_time(12345)
        self.assertIsInstance(weekday, int)
        self.assertIsInstance(hour, int)
        self.assertIsInstance(minute, int)


class TestAskWorkSchedule(unittest.TestCase):
    """Test cases for the ask_work_schedule function."""

    def setUp(self):
        """Set up a WorkScheduleWeek for ask_work_schedule tests."""
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))  # Monday midnight

        # Create a workday with morning and afternoon shifts
        workday = WorkScheduleDay()
        workday.set_time(8, 0, 12, 0, capacity=2)   # Morning shift
        workday.set_time(13, 0, 17, 0, capacity=3)  # Afternoon shift

        # Create weekend (no work)
        weekend = WorkScheduleDay()

        self.week_schedule = WorkScheduleWeek(
            workday, workday, workday, workday, workday, weekend, weekend
        )

    def test_during_morning_shift(self):
        """Test time during the morning shift."""
        # 10 AM (600 minutes)
        is_active, time_to_wait, capacity = ask_work_schedule(600, self.week_schedule)
        self.assertTrue(is_active)
        self.assertEqual(time_to_wait, 0)
        self.assertEqual(capacity, 2)

    def test_during_afternoon_shift(self):
        """Test time during the afternoon shift."""
        # 3 PM (900 minutes)
        is_active, time_to_wait, capacity = ask_work_schedule(900, self.week_schedule)
        self.assertTrue(is_active)
        self.assertEqual(time_to_wait, 0)
        self.assertEqual(capacity, 3)

    def test_outside_shift_before_work(self):
        """Test time before the first shift starts."""
        # 6 AM (360 minutes)
        is_active, time_to_wait, capacity = ask_work_schedule(360, self.week_schedule)
        self.assertFalse(is_active)
        self.assertGreater(time_to_wait, 0)
        self.assertIsNone(capacity)

        # Should wait until 8 AM (120 minutes = 2 hours)
        self.assertEqual(time_to_wait, 120)

    def test_outside_shift_between_shifts(self):
        """Test time between morning and afternoon shifts."""
        # 12:30 PM (750 minutes) - between shifts
        is_active, time_to_wait, capacity = ask_work_schedule(750, self.week_schedule)
        self.assertFalse(is_active)
        self.assertGreater(time_to_wait, 0)
        self.assertIsNone(capacity)

        # Should wait until 1 PM (30 minutes)
        self.assertEqual(time_to_wait, 30)

    def test_outside_shift_after_last_shift(self):
        """Test time after the last shift ends."""
        # 6 PM (1080 minutes)
        is_active, time_to_wait, capacity = ask_work_schedule(1080, self.week_schedule)
        self.assertFalse(is_active)
        self.assertGreater(time_to_wait, 0)
        self.assertIsNone(capacity)

    def test_weekend_schedule(self):
        """Test schedule during weekend (no work)."""
        # Saturday 10 AM (5 days * 1440 minutes + 600 minutes)
        saturday_time = 5 * 1440 + 600
        is_active, time_to_wait, capacity = ask_work_schedule(saturday_time, self.week_schedule)
        self.assertFalse(is_active)
        self.assertGreater(time_to_wait, 0)
        self.assertIsNone(capacity)

    def test_exact_shift_start(self):
        """Test time exactly at shift start."""
        # 8 AM (480 minutes)
        is_active, time_to_wait, capacity = ask_work_schedule(480, self.week_schedule)
        self.assertTrue(is_active)
        self.assertEqual(time_to_wait, 0)
        self.assertEqual(capacity, 2)

    def test_exact_shift_end(self):
        """Test time exactly at shift end."""
        # 12 PM (720 minutes) - end of morning shift
        is_active, time_to_wait, capacity = ask_work_schedule(720, self.week_schedule)
        self.assertFalse(is_active)  # Shift ends at 12:00, so not active
        self.assertGreater(time_to_wait, 0)
        self.assertIsNone(capacity)

    def test_week_wrap_around(self):
        """Test schedule wrap around from end of week to beginning."""
        # Create schedule that works on Monday but not other days
        monday_only = WorkScheduleDay()
        monday_only.set_time(9, 0, 17, 0, capacity=1)

        off_day = WorkScheduleDay()

        week_schedule = WorkScheduleWeek(
            monday_only, off_day, off_day, off_day, off_day, off_day, off_day
        )

        # Test late Sunday (should wait until Monday)
        sunday_evening = 6 * 1440 + 1200  # Sunday 8 PM
        is_active, time_to_wait, capacity = ask_work_schedule(sunday_evening, week_schedule)
        self.assertFalse(is_active)
        self.assertGreater(time_to_wait, 0)
        self.assertIsNone(capacity)


class TestLoadWorkScheduleFromCsv(unittest.TestCase):
    """Test cases for loading work schedules from CSV files."""

    def setUp(self):
        DateTime.set(datetime(2024, 1, 1, 0, 0, 0))

    def test_load_work_schedule_basic(self):
        """Test loading a basic work schedule from CSV."""
        csv_content = """day,start_hour,start_minute,end_hour,end_minute,capacity
Monday,9,0,17,0,2
Tuesday,8,30,16,30,3
Wednesday,10,0,18,0,1"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            week_schedule = load_work_schedule_from_csv(temp_file)
            schedule, _ = week_schedule.get()

            # Should have 3 shifts (Mon, Tue, Wed)
            self.assertEqual(len(schedule), 3)

        finally:
            os.unlink(temp_file)

    def test_load_work_schedule_with_config(self):
        """Test loading work schedule with custom CSV configuration."""
        csv_content = """day;start_hour;start_minute;end_hour;end_minute;capacity
Monday;9;0;17;0;2
Friday;13;30;21;30;1"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            config = {'sep': ';'}
            week_schedule = load_work_schedule_from_csv(temp_file, config)
            schedule, _ = week_schedule.get()

            # Should have 2 shifts
            self.assertEqual(len(schedule), 2)

        finally:
            os.unlink(temp_file)

    def test_load_work_schedule_all_days(self):
        """Test loading work schedule for all days of the week."""
        csv_content = """day,start_hour,start_minute,end_hour,end_minute,capacity
Monday,9,0,17,0,2
Tuesday,9,0,17,0,2
Wednesday,9,0,17,0,2
Thursday,9,0,17,0,2
Friday,9,0,17,0,2
Saturday,10,0,14,0,1
Sunday,10,0,14,0,1"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            week_schedule = load_work_schedule_from_csv(temp_file)
            schedule, _ = week_schedule.get()

            # Should have 7 shifts (all days)
            self.assertEqual(len(schedule), 7)

        finally:
            os.unlink(temp_file)

    def test_load_work_schedule_multiple_shifts_per_day(self):
        """Test loading work schedule with multiple shifts per day."""
        csv_content = """day,start_hour,start_minute,end_hour,end_minute,capacity
Monday,6,0,14,0,2
Monday,14,0,22,0,3
Tuesday,8,0,16,0,1"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            week_schedule = load_work_schedule_from_csv(temp_file)
            schedule, _ = week_schedule.get()

            # Should have 3 shifts (2 on Monday, 1 on Tuesday)
            self.assertEqual(len(schedule), 3)

        finally:
            os.unlink(temp_file)

    def test_load_work_schedule_empty_file(self):
        """Test loading work schedule from empty CSV file."""
        csv_content = """day,start_hour,start_minute,end_hour,end_minute,capacity"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            week_schedule = load_work_schedule_from_csv(temp_file)
            schedule, _ = week_schedule.get()

            # Should have no shifts
            self.assertEqual(len(schedule), 0)

        finally:
            os.unlink(temp_file)

    def test_load_work_schedule_edge_cases(self):
        """Test loading work schedule with edge case values."""
        csv_content = """day,start_hour,start_minute,end_hour,end_minute,capacity
Monday,0,0,24,0,0
Tuesday,23,59,24,0,10"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            week_schedule = load_work_schedule_from_csv(temp_file)
            schedule, _ = week_schedule.get()

            # Should have 2 shifts with edge case times
            self.assertEqual(len(schedule), 2)

        finally:
            os.unlink(temp_file)


class TestWorkScheduleIntegration(unittest.TestCase):
    """Integration tests for work schedule components."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))  # Monday

    def test_complete_workflow(self):
        """Test a complete workflow from creation to querying."""
        # Create complex schedule
        workday = WorkScheduleDay()
        workday.set_time(8, 0, 12, 0, capacity=2)   # Morning
        workday.set_time(13, 0, 17, 0, capacity=3)  # Afternoon
        workday.set_time(18, 0, 22, 0, capacity=1)  # Evening

        weekend = WorkScheduleDay()
        weekend.set_time(10, 0, 14, 0, capacity=1)  # Reduced weekend hours

        week = WorkScheduleWeek(
            workday, workday, workday, workday, workday, weekend, weekend
        )

        # Test various times throughout the week
        test_times = [
            (480, True, 2),    # 8 AM Monday - morning shift
            (720, False, None),  # 12 PM Monday - between shifts
            (780, True, 3),    # 1 PM Monday - afternoon shift
            (1080, True, 1),   # 6 PM Monday - evening shift
            (1440, False, None),  # 12 AM Tuesday - no shift
        ]

        for time_minutes, expected_active, expected_capacity in test_times:
            is_active, time_to_wait, capacity = ask_work_schedule(time_minutes, week)
            self.assertEqual(is_active, expected_active)
            self.assertEqual(capacity, expected_capacity)

            if not is_active:
                self.assertGreater(time_to_wait, 0)
            else:
                self.assertEqual(time_to_wait, 0)

    def test_csv_to_query_workflow(self):
        """Test complete workflow from CSV loading to schedule querying."""
        csv_content = """day,start_hour,start_minute,end_hour,end_minute,capacity
Monday,9,0,17,0,2
Tuesday,8,0,16,0,3
Wednesday,10,0,18,0,1
Thursday,9,0,17,0,2
Friday,8,0,16,0,3"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            # Load from CSV
            week_schedule = load_work_schedule_from_csv(temp_file)

            # Test specific queries
            # Monday 10 AM
            is_active, _, capacity = ask_work_schedule(600, week_schedule)  # 10*60 = 600
            self.assertTrue(is_active)
            self.assertEqual(capacity, 2)

            # Tuesday 2 PM
            is_active, _, capacity = ask_work_schedule(1440 + 840, week_schedule)  # 1 day + 14*60
            self.assertTrue(is_active)
            self.assertEqual(capacity, 3)

            # Saturday (no work)
            is_active, time_to_wait, capacity = ask_work_schedule(5 * 1440 + 600, week_schedule)
            self.assertFalse(is_active)
            self.assertIsNone(capacity)
            self.assertGreater(time_to_wait, 0)

        finally:
            os.unlink(temp_file)

    def test_steps_in_time_integration(self):
        """Test steps_in_time function integration with schedule."""
        # Test conversion consistency
        original_time = DateTime.map_time_to_steps(2, 15, 30)  # 2 days, 15:30
        weekday, hour, minute = steps_in_time(original_time)

        self.assertEqual(weekday, 2)  # Wednesday
        self.assertEqual(hour, 15)
        self.assertEqual(minute, 30)

        # Test with schedule
        workday = WorkScheduleDay()
        workday.set_time(hour, minute, hour + 2, minute, capacity=1)

        week = WorkScheduleWeek(
            WorkScheduleDay(), WorkScheduleDay(), workday, WorkScheduleDay(),
            WorkScheduleDay(), WorkScheduleDay(), WorkScheduleDay()
        )

        is_active, _, capacity = ask_work_schedule(original_time, week)
        self.assertTrue(is_active)
        self.assertEqual(capacity, 1)


if __name__ == '__main__':
    unittest.main()
