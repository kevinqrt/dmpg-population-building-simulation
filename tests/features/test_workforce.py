import unittest
import simpy
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.core.components.work_schedule import WorkScheduleDay, WorkScheduleWeek
from src.core.components.worker_pool import (
    Worker, WorkerPool, print_worker_utilization_for_pool,
    print_all_worker_pools_summary, load_workers_from_csv
)
from src.core.components.date_time import DateTime
from src.core.components.model import Model


class TestWorker(unittest.TestCase):
    """Test cases for the Worker class."""

    def test_worker_initialization(self):
        """Test Worker initialization with different ID types."""
        # String ID
        worker = Worker("Worker_1")
        self.assertEqual(worker.id, "Worker_1")
        self.assertEqual(worker.allocations, 0)
        self.assertEqual(worker.total_busy_time, 0.0)
        self.assertIsNone(worker.busy_since)
        self.assertIsNone(worker.busy_with)

        # Numeric ID (should be converted to string)
        worker = Worker("123")
        self.assertEqual(worker.id, "123")

    def test_worker_repr(self):
        """Test Worker string representation."""
        worker = Worker("TestWorker")
        self.assertEqual(repr(worker), "Worker(TestWorker)")

    def test_start_assignment_fresh_worker(self):
        """Test starting assignment on a fresh worker."""
        worker = Worker("W1")
        start_time = 10.0
        server_name = "Server1"

        worker.start_assignment(server_name, start_time)

        self.assertEqual(worker.allocations, 1)
        self.assertEqual(worker.busy_since, start_time)
        self.assertEqual(worker.busy_with, server_name)
        self.assertEqual(worker.total_busy_time, 0.0)  # No previous busy time

    def test_start_assignment_worker_with_history(self):
        """Test starting assignment on worker with previous busy time."""
        worker = Worker("W1")

        # First assignment
        worker.start_assignment("Server1", 5.0)
        worker.end_assignment("Server1", 10.0)

        # Second assignment
        worker.start_assignment("Server2", 15.0)

        self.assertEqual(worker.allocations, 2)
        self.assertEqual(worker.busy_since, 15.0)
        self.assertEqual(worker.busy_with, "Server2")
        self.assertEqual(worker.total_busy_time, 5.0)

    def test_end_assignment_success(self):
        """Test successful end of assignment."""
        worker = Worker("W1")
        worker.start_assignment("Server1", 5.0)

        duration = worker.end_assignment("Server1", 15.0)

        self.assertEqual(duration, 10.0)
        self.assertEqual(worker.total_busy_time, 10.0)
        self.assertIsNone(worker.busy_since)
        self.assertIsNone(worker.busy_with)

    def test_end_assignment_not_assigned(self):
        """Test ending assignment when worker wasn't assigned."""
        worker = Worker("W1")

        with patch('logging.warning') as mock_warning:
            duration = worker.end_assignment("Server1", 15.0)

        self.assertEqual(duration, 0)
        mock_warning.assert_called_once()

    def test_multiple_assignments_cycle(self):
        """Test multiple assignment cycles to verify state management."""
        worker = Worker("W1")

        # First cycle
        worker.start_assignment("Server1", 0.0)
        duration1 = worker.end_assignment("Server1", 5.0)

        # Second cycle
        worker.start_assignment("Server2", 10.0)
        duration2 = worker.end_assignment("Server2", 18.0)

        self.assertEqual(duration1, 5.0)
        self.assertEqual(duration2, 8.0)
        self.assertEqual(worker.total_busy_time, 13.0)
        self.assertEqual(worker.allocations, 2)


class TestWorkerPoolInitialization(unittest.TestCase):
    """Test cases for WorkerPool initialization."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))

        # Create a work schedule with a full-day shift with capacity 3
        self.work_day = WorkScheduleDay()
        self.work_day.set_time(0, 0, 24, 0, capacity=3)
        self.week = WorkScheduleWeek(
            self.work_day, self.work_day, self.work_day,
            self.work_day, self.work_day, self.work_day, self.work_day
        )

        self.workers = [Worker(f"W{i + 1}") for i in range(5)]
        self.env = simpy.Environment()

    def test_initial_worker_pool_with_provided_workers(self):
        """Test WorkerPool initialization with provided workers."""
        pool = WorkerPool(self.env, self.week, workers=self.workers)
        self.env.run(until=self.env.now + 1)

        # With a capacity of 3, the first 3 workers should be in the pool
        expected_ids = ["W1", "W2", "W3"]
        actual_ids = [worker.id for worker in pool.store.items]
        self.assertEqual(actual_ids, expected_ids)

        # Check that worker locks are created for all workers
        self.assertEqual(len(pool.worker_locks), 5)
        for worker in self.workers:
            self.assertIn(worker.id, pool.worker_locks)
            self.assertIsInstance(pool.worker_locks[worker.id], simpy.Resource)

    def test_worker_pool_without_provided_workers(self):
        """Test WorkerPool initialization without provided workers (fallback)."""
        pool = WorkerPool(self.env, self.week)
        self.env.run(until=self.env.now + 1)

        # Should create default workers based on schedule capacity
        self.assertEqual(len(pool.workers), 3)  # Capacity is 3
        for i, worker in enumerate(pool.workers):
            self.assertEqual(worker.id, f"Worker_{i + 1}")


class TestWorkerPoolScheduleManagement(unittest.TestCase):
    """Test cases for WorkerPool schedule management."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))  # Monday
        self.env = simpy.Environment()

    def test_schedule_transitions(self):
        """Test WorkerPool behavior during schedule transitions."""
        # Create a schedule with two shifts per day
        work_day = WorkScheduleDay()
        work_day.set_time(8, 0, 12, 0, capacity=2)   # Morning shift: 2 workers
        work_day.set_time(13, 0, 17, 0, capacity=3)  # Afternoon shift: 3 workers

        week = WorkScheduleWeek(work_day, work_day, work_day, work_day, work_day, work_day, work_day)

        workers = [Worker(f"W{i}") for i in range(5)]
        pool = WorkerPool(self.env, week, workers=workers)

        # Before morning shift (7:00 AM = 420 minutes)
        self.env.run(until=420)
        self.assertEqual(len(pool.store.items), 0)

        # During morning shift (10:00 AM = 600 minutes)
        self.env.run(until=600)
        self.assertEqual(len(pool.store.items), 2)

        # Between shifts (12:30 PM = 750 minutes)
        self.env.run(until=750)
        self.assertEqual(len(pool.store.items), 0)

        # During afternoon shift (15:00 PM = 900 minutes)
        self.env.run(until=900)
        self.assertEqual(len(pool.store.items), 3)

    def test_weekly_schedule_wrap_around(self):
        """Test that schedule correctly wraps around from end of week to beginning."""
        # Create schedule that only works on Monday
        monday = WorkScheduleDay()
        monday.set_time(0, 0, 24, 0, capacity=2)

        off_day = WorkScheduleDay()  # No shifts

        week = WorkScheduleWeek(monday, off_day, off_day, off_day, off_day, off_day, off_day)

        workers = [Worker(f"W{i}") for i in range(3)]
        pool = WorkerPool(self.env, week, workers=workers)

        # Monday (day 0): should have workers
        self.env.run(until=100)
        self.assertEqual(len(pool.store.items), 2)

        # Tuesday (day 1): should be off
        self.env.run(until=24 * 60 + 100)  # 24 hours + 100 minutes
        self.assertEqual(len(pool.store.items), 0)

        # Next Monday (day 7 wraps to day 0): should have workers again
        self.env.run(until=7 * 24 * 60 + 100)  # 7 days + 100 minutes
        self.assertEqual(len(pool.store.items), 2)


class TestWorkerPoolRequestRelease(unittest.TestCase):
    """Test cases for worker request and release operations."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))
        self.work_day = WorkScheduleDay()
        self.work_day.set_time(0, 0, 24, 0, capacity=3)
        self.week = WorkScheduleWeek(
            self.work_day, self.work_day, self.work_day,
            self.work_day, self.work_day, self.work_day, self.work_day
        )
        self.workers = [Worker(f"W{i + 1}") for i in range(5)]
        self.env = simpy.Environment()
        self.pool = WorkerPool(self.env, self.week, workers=self.workers)
        self.env.run(until=self.env.now + 1)

    def test_worker_request_and_release(self):
        """Test basic worker request and release cycle."""
        def worker_process(env, pool, hold_time):
            worker = yield pool.store.get(lambda w: True)
            yield env.timeout(hold_time)
            yield pool.store.put(worker)

        # Initially, pool should have 3 workers
        self.assertEqual(len(self.pool.store.items), 3)

        # Start a process that holds a worker for 5 time units
        self.env.process(worker_process(self.env, self.pool, 5))

        # Run a little time so that one worker is taken
        self.env.run(until=self.env.now + 0.1)
        self.assertEqual(len(self.pool.store.items), 2)

        # Run until after the worker is released
        self.env.run(until=self.env.now + 5)
        self.env.run(until=self.env.now + 0.1)
        self.assertEqual(len(self.pool.store.items), 3)

    def test_specific_worker_request(self):
        """Test requesting a specific worker by ID."""
        def request_specific_worker(env, pool, worker_id):
            worker = yield pool.store.get(lambda w: w.id == worker_id)
            self.assertEqual(worker.id, worker_id)
            yield env.timeout(1)
            yield pool.store.put(worker)

        self.env.process(request_specific_worker(self.env, self.pool, "W2"))
        self.env.run(until=self.env.now + 2)

        # After process completes, pool should be back to 3 workers
        self.assertEqual(len(self.pool.store.items), 3)

    def test_worker_filtering(self):
        """Test worker filtering functionality."""
        def request_with_filter(env, pool):
            # Request worker with specific condition
            worker = yield pool.store.get(lambda w: w.id.startswith("W"))
            yield env.timeout(1)
            yield pool.store.put(worker)

        self.env.process(request_with_filter(self.env, self.pool))
        self.env.run(until=self.env.now + 2)

        self.assertEqual(len(self.pool.store.items), 3)


class TestWorkerPoolConcurrentRequests(unittest.TestCase):
    """Test cases for concurrent worker requests."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))
        self.work_day = WorkScheduleDay()
        self.work_day.set_time(0, 0, 24, 0, capacity=3)
        self.week = WorkScheduleWeek(
            self.work_day, self.work_day, self.work_day,
            self.work_day, self.work_day, self.work_day, self.work_day
        )
        self.workers = [Worker(f"W{i + 1}") for i in range(5)]
        self.env = simpy.Environment()
        self.pool = WorkerPool(self.env, self.week, workers=self.workers)
        self.env.run(until=self.env.now + 1)

    def test_concurrent_requests(self):
        """Test concurrent worker requests with limited capacity."""
        results = []

        def request_worker(env, pool, hold_time, idx):
            worker = yield pool.store.get(lambda w: True)
            results.append((idx, worker.id))
            yield env.timeout(hold_time)
            yield pool.store.put(worker)

        # Start 4 processes concurrently (capacity is 3, so one will wait)
        for i in range(4):
            self.env.process(request_worker(self.env, self.pool, 3, i))

        self.env.run(until=self.env.now + 10)
        self.env.run(until=self.env.now + 0.1)

        self.assertEqual(len(results), 4)
        self.assertEqual(len(self.pool.store.items), 3)


class TestWorkerPoolUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""

    def setUp(self):
        # Mock Model to avoid dependencies
        self.mock_model = MagicMock()
        Model._instance = self.mock_model

    def tearDown(self):
        # Clean up Model instance
        Model._instance = None

    @patch('builtins.print')
    def test_print_worker_utilization_for_pool(self, mock_print):
        """Test worker utilization printing function."""
        # Create mock workers with utilization data
        workers = [
            Worker("W1"),
            Worker("W2"),
            Worker("W3")
        ]

        # Set up utilization data
        workers[0].allocations = 5
        workers[0].total_busy_time = 45.0
        workers[1].allocations = 3
        workers[1].total_busy_time = 30.0
        workers[2].allocations = 7
        workers[2].total_busy_time = 60.0

        # Mock worker pool
        mock_pool = MagicMock()
        mock_pool.workers = workers

        # Mock Model.worker_pools
        self.mock_model.worker_pools = {'test_pool': mock_pool}

        # Test the function
        print_worker_utilization_for_pool('test_pool', 100.0)

        # Verify print was called multiple times (header, workers, summary)
        self.assertTrue(mock_print.call_count > 5)

        # Check that worker information is included in output
        printed_content = ''.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('W1', printed_content)
        self.assertIn('W2', printed_content)
        self.assertIn('W3', printed_content)
        self.assertIn('WORKFORCE UTILIZATION', printed_content)

    @patch('builtins.print')
    def test_print_worker_utilization_for_nonexistent_pool(self, mock_print):
        """Test printing utilization for non-existent pool."""
        self.mock_model.worker_pools = {}

        print_worker_utilization_for_pool('nonexistent_pool', 100.0)

        # Should not print anything for non-existent pool
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_print_all_worker_pools_summary(self, mock_print):
        """Test summary printing for all worker pools."""
        # Create mock pools
        workers1 = [Worker("P1_W1"), Worker("P1_W2")]
        workers1[0].total_busy_time = 25.0
        workers1[1].total_busy_time = 35.0

        workers2 = [Worker("P2_W1")]
        workers2[0].total_busy_time = 50.0

        pool1 = MagicMock()
        pool1.workers = workers1
        pool2 = MagicMock()
        pool2.workers = workers2

        self.mock_model.worker_pools = {
            'pool1': pool1,
            'pool2': pool2
        }

        print_all_worker_pools_summary(100.0)

        # Should print summary information
        self.assertTrue(mock_print.call_count > 3)
        printed_content = ''.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('OVERALL WORKFORCE SUMMARY', printed_content)
        self.assertIn('pool1', printed_content)
        self.assertIn('pool2', printed_content)

    @patch('builtins.print')
    def test_print_all_worker_pools_empty(self, mock_print):
        """Test summary printing when no worker pools exist."""
        self.mock_model.worker_pools = {}

        print_all_worker_pools_summary(100.0)

        # Should not print anything when no pools exist
        mock_print.assert_not_called()

    def test_load_workers_from_csv(self):
        """Test loading workers from CSV file."""
        # Create temporary CSV file
        csv_content = """id
Worker_1
Worker_2
Worker_3"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            # Test loading
            workers = load_workers_from_csv(temp_file)

            self.assertEqual(len(workers), 3)
            self.assertEqual(workers[0].id, "Worker_1")
            self.assertEqual(workers[1].id, "Worker_2")
            self.assertEqual(workers[2].id, "Worker_3")

        finally:
            # Clean up
            os.unlink(temp_file)


class TestWorkerPoolEdgeCases(unittest.TestCase):
    """Test cases for edge cases and error conditions."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 0, 0, 0))
        self.env = simpy.Environment()

    def test_more_workers_than_max_capacity(self):
        """Test WorkerPool with more workers than maximum schedule capacity."""
        work_day = WorkScheduleDay()
        work_day.set_time(9, 0, 17, 0, capacity=2)
        week = WorkScheduleWeek(work_day, work_day, work_day, work_day, work_day, work_day, work_day)

        # Provide 5 workers for a pool with max capacity 2
        workers = [Worker(f"W{i}") for i in range(5)]
        pool = WorkerPool(self.env, week, workers=workers)

        # During work hours, should only have 2 workers available
        self.env.run(until=600)  # 10 AM
        self.assertEqual(len(pool.store.items), 2)

        # Extra workers should still exist but not be in the store
        self.assertEqual(len(pool.workers), 5)


class TestWorkerPoolIntegration(unittest.TestCase):
    """Integration tests for WorkerPool with other components."""

    def setUp(self):
        DateTime.set(datetime(2024, 4, 1, 8, 0, 0))  # 8 AM on Monday
        self.env = simpy.Environment()

    def test_worker_pool_with_model_integration(self):
        """Test WorkerPool integration with Model class."""
        # Create work schedule
        work_day = WorkScheduleDay()
        work_day.set_time(8, 0, 16, 0, capacity=3)
        week = WorkScheduleWeek(work_day, work_day, work_day, work_day, work_day, work_day, work_day)

        # Create workers
        workers = [Worker(f"Worker_{i}") for i in range(5)]

        # Create pool
        pool = WorkerPool(self.env, week, workers=workers)

        # Verify Model integration points
        self.assertEqual(len(pool.workers), 5)
        self.assertEqual(len(pool.worker_locks), 5)

        # Verify worker locks are Resources
        for worker_id, lock in pool.worker_locks.items():
            self.assertIsInstance(lock, simpy.Resource)
            self.assertEqual(lock.capacity, 1)

    def test_realistic_simulation_scenario(self):
        """Test a realistic simulation scenario with varying workload."""
        # Create realistic work schedule (Mon-Fri, 9-5)
        workday = WorkScheduleDay()
        workday.set_time(9, 0, 17, 0, capacity=4)

        weekend = WorkScheduleDay()  # No work on weekends

        week = WorkScheduleWeek(workday, workday, workday, workday, workday, weekend, weekend)

        # Create workers
        workers = [Worker(f"Employee_{i}") for i in range(6)]
        pool = WorkerPool(self.env, week, workers=workers)

        work_assignments = []

        def simulate_work_process(env, pool, process_id, start_time, duration):
            """Simulate a work process that requires a worker."""
            yield env.timeout(start_time)  # Wait until start time

            try:
                worker = yield pool.store.get(lambda w: True)
                worker.start_assignment(f"Process_{process_id}", env.now)

                yield env.timeout(duration)

                worker.end_assignment(f"Process_{process_id}", env.now)
                work_assignments.append((process_id, worker.id, duration))

                yield pool.store.put(worker)

            except Exception:
                pass  # Handle case where no workers available

        # Schedule various work processes during business hours
        # (assuming simulation starts at 8 AM, work starts at 9 AM = 60 minutes later)
        processes = [
            (1, 60, 120),   # Process 1: start at 9 AM, duration 2 hours
            (2, 90, 180),   # Process 2: start at 9:30 AM, duration 3 hours
            (3, 120, 60),   # Process 3: start at 10 AM, duration 1 hour
            (4, 150, 240),  # Process 4: start at 10:30 AM, duration 4 hours
        ]

        for process_id, start_time, duration in processes:
            self.env.process(simulate_work_process(self.env, pool, process_id, start_time, duration))

        # Run simulation for a full work day
        self.env.run(until=600)  # 10 hours

        # Verify work was completed
        self.assertGreater(len(work_assignments), 0)

        # Verify worker utilization tracking
        for worker in workers:
            if worker.allocations > 0:
                self.assertGreater(worker.total_busy_time, 0)


if __name__ == '__main__':
    unittest.main()
