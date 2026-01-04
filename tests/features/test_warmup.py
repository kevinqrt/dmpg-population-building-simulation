import unittest
from src.core.simulation.simulation import run_simulation, run_replications
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.global_imports import random
import src.core.global_imports as gi


def setup_model(env):
    source = Source(env, "Source1", (random.expovariate, 1 / 1.25))
    server = Server(env, "Server1", (random.expovariate, 1))
    sink = Sink(env, "Sink1")

    source.connect(server)
    server.connect(sink)


class TestWarmUp(unittest.TestCase):
    def test_no_warm_up(self):
        """
        Verify statistics when no warm-up is applied.
        """
        pivot_table = run_simulation(model=setup_model, steps=1000)
        # Verify that entities are created without a warm-up period
        created_entities = pivot_table.at[('Entity', 'Entity', 'NumberCreated'), 'Value']
        self.assertGreater(created_entities, 0, "Entities were not created during the simulation.")

    def test_with_warm_up(self):
        """
        Verify statistics when a warm-up period is applied.
        """
        warm_up_duration = 200
        pivot_table = run_simulation(model=setup_model, steps=1000, warm_up=warm_up_duration)
        self.assertEqual(warm_up_duration, gi.DURATION_WARM_UP, "Warm-up duration was not set correctly.")
        # Ensure entities are still processed after warm-up
        created_entities = pivot_table.at[('Entity', 'Entity', 'NumberCreated'), 'Value']
        self.assertGreater(created_entities, 0, "Entities were not processed after the warm-up period.")

    def test_compare_with_and_without_warm_up(self):
        """
        Compare results with and without warm-up to ensure warm-up behavior works as expected.
        """
        no_warm_up_pivot = run_simulation(model=setup_model, steps=1000)
        with_warm_up_pivot = run_simulation(model=setup_model, steps=1000, warm_up=200)

        # Server processing statistics
        avg_time_no_warm_up = no_warm_up_pivot.at[('Server', 'Server1', 'TimeProcessing (average)'), 'Value']
        avg_time_with_warm_up = with_warm_up_pivot.at[('Server', 'Server1', 'TimeProcessing (average)'), 'Value']
        self.assertNotEqual(avg_time_no_warm_up, avg_time_with_warm_up,
                            "Warm-up did not affect average processing time.")

        # Server utilization statistics
        util_no_warm_up = no_warm_up_pivot.at[('Server', 'Server1', 'ScheduledUtilization'), 'Value']
        util_with_warm_up = with_warm_up_pivot.at[('Server', 'Server1', 'ScheduledUtilization'), 'Value']
        self.assertNotEqual(util_no_warm_up, util_with_warm_up,
                            "Warm-up did not affect server utilization.")

        # Server queue statistics
        queue_no_warm_up = no_warm_up_pivot.at[('Server', 'Server1', 'EntitiesInQueue (average)'), 'Value']
        queue_with_warm_up = with_warm_up_pivot.at[('Server', 'Server1', 'EntitiesInQueue (average)'), 'Value']
        self.assertNotEqual(queue_no_warm_up, queue_with_warm_up,
                            "Warm-up did not affect average queue length.")

        # Entity statistics
        in_system_no_warm_up = no_warm_up_pivot.at[('Entity', 'Entity', 'NumberInSystem (average)'), 'Value']
        in_system_with_warm_up = with_warm_up_pivot.at[('Entity', 'Entity', 'NumberInSystem (average)'), 'Value']
        self.assertNotEqual(in_system_no_warm_up, in_system_with_warm_up,
                            "Warm-up did not affect number of entities in system.")

        # Source statistics
        created_no_warm_up = no_warm_up_pivot.at[('Source', 'Source1', 'NumberCreated'), 'Value']
        created_with_warm_up = with_warm_up_pivot.at[('Source', 'Source1', 'NumberCreated'), 'Value']
        self.assertNotEqual(created_no_warm_up, created_with_warm_up,
                            "Warm-up did not affect number of entities created.")

        # Sink statistics
        entered_sink_no_warm_up = no_warm_up_pivot.at[('Sink', 'Sink1', 'NumberEntered'), 'Value']
        entered_sink_with_warm_up = with_warm_up_pivot.at[('Sink', 'Sink1', 'NumberEntered'), 'Value']
        self.assertNotEqual(entered_sink_no_warm_up, entered_sink_with_warm_up,
                            "Warm-up did not affect number of entities entering sink.")

        # Derived statistic - throughput ratio (entities completed vs created)
        throughput_no_warm_up = entered_sink_no_warm_up / created_no_warm_up
        throughput_with_warm_up = entered_sink_with_warm_up / created_with_warm_up
        self.assertNotEqual(round(throughput_no_warm_up, 4), round(throughput_with_warm_up, 4),
                            "Warm-up did not affect throughput ratio.")

    def test_edge_case_excessive_warm_up(self):
        """
        Test case where warm-up exceeds total simulation time.
        """
        with self.assertRaises(ValueError):
            run_simulation(model=setup_model, steps=1000, warm_up=2000)

    def test_edge_case_full_warm_up(self):
        """
        Test case where warm-up equals total simulation time.
        """
        pivot_table = run_simulation(model=setup_model, steps=1000, warm_up=999.99)

        # When warm-up equals simulation time, statistics should be minimal or zero
        destroyed_entities = pivot_table.at[('Entity', 'Entity', 'NumberDestroyed'), 'Value']
        self.assertEqual(destroyed_entities, 0, "Entities should not have been processed.")

    def test_warm_up_in_replications(self):
        """
        Verify that warm-up works in replicated simulations.
        """
        pivot_table = run_replications(model=setup_model, steps=1000, num_replications=10, warm_up=996)

        destroyed_entities = pivot_table.at[('Entity', 'Entity', 'NumberDestroyed'), 'Average']

        # Check that entities are processed after the warm-up period
        self.assertGreater(destroyed_entities, 0, "Entities were not processed after the warm-up period in replications.")

        # Check that the number of destroyed entities is less than 10
        self.assertLess(destroyed_entities, 10, "The number of destroyed entities exceeded the expected threshold (10).")
