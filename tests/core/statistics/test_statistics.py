import unittest
from src.core.components.server import Server
from src.core.components.entity import Entity, EntityManager
from src.core.components.sink import Sink
from src.core.statistics.stats import calculate_units_utilized, calculate_all_stats
import simpy
from database.base.database_config import initialize_db, drop_db
from database.replication.replication_db import store_run_replication, create_pivot_run_replication


class TestStatistics(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_units_utilized_calculation(self):
        # This test case checks if the units utilized calculation works correctly.
        server = Server(self.env, "TestServerStats", capacity=2,
                        processing_time_distribution_with_parameters=(lambda: 2,))
        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        entities = [Entity(f"Entity{i + 1}", self.env.now) for i in range(4)]
        for entity in entities:
            server.handle_entity_arrival(entity)

        self.env.run(until=4.001)

        # Print the recorded utilization times for debugging
        print("Recorded units utilized over time:", server.units_utilized_over_time)

        # Print the number of processed entities for debugging
        print("Number of entities processed:", server.number_exited_pivot_table)

        expected_units_utilized = 2
        actual_units_utilized = calculate_units_utilized(server.units_utilized_over_time, server.capacity, self.env.now)
        self.assertAlmostEqual(expected_units_utilized, actual_units_utilized,
                               msg="Calculated units utilized does not match the expected result")

    def test_average_processing_time(self):
        # This test checks the average processing time calculation for entities in a server.
        server = Server(self.env, "TestServerAvgProcTime", capacity=1,
                        processing_time_distribution_with_parameters=(lambda: 3,))
        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        for _ in range(5):
            server.handle_entity_arrival(Entity("TestEntity", self.env.now))
        self.env.run(until=100)

        expected_avg_processing_time = 3  # Assuming fixed processing time of 3
        actual_avg_processing_time = server.total_processing_time_pivot_table / server.total_entities_processed_pivot_table
        self.assertEqual(expected_avg_processing_time, actual_avg_processing_time,
                         "Average processing time is not as expected")

    def test_system_throughput(self):
        # This test case checks the system throughput calculation.
        server = Server(self.env, "TestServerThroughput", capacity=2,
                        processing_time_distribution_with_parameters=(lambda: 4,))
        sink = Sink(self.env, "TestSinkThroughput")
        server.connect(sink)

        self.env.run(until=100)

        expected_throughput = server.total_entities_processed_pivot_table / self.env.now
        actual_throughput = len(sink.processed_entities) / self.env.now
        self.assertAlmostEqual(expected_throughput, actual_throughput,
                               msg="System throughput calculation is incorrect")

    def test_create_pivot_table(self):
        # Test the pivot table creation from simulation statistics
        entity_stats = {'NumberCreated': 10, 'NumberDestroyed': 8}
        server_stats = [{'Server': 'Server1', 'ScheduledUtilization': 80, 'UnitsUtilized': 1.2}]
        sink_stats = {'Sink1': {'AvgTimeInSystem': 5.0}}
        source_stats = {'Source1': {'NumberExited': 8}}

        stats = calculate_all_stats(
            [entity_stats],
            {'Server1': server_stats},
            {'Sink1': [sink_stats['Sink1']]},
            {'Source1': [source_stats['Source1']]},
            {},
            {},
            {},
            {},
            entity_stat_names=['NumberCreated', 'NumberDestroyed'],
            server_stat_names=['ScheduledUtilization', 'UnitsUtilized'],
            sink_stat_names=['AvgTimeInSystem'],
            source_stat_names=['NumberExited'],
            vehicle_stat_names=[],
            storage_stat_names=[],
            separator_stat_names=[],
            combiner_stat_names=[]
        )

        drop_db()
        initialize_db()
        store_run_replication(stats)
        pivot_table = create_pivot_run_replication()

        # Check if the pivot table includes correct stats for each component
        self.assertIn(('Entity', 'Entity', 'NumberCreated'), pivot_table.index,
                      "Pivot table missing Entity NumberCreated statistic")
        self.assertIn(('Server', 'Server1', 'ScheduledUtilization'), pivot_table.index,
                      "Pivot table missing Server ScheduledUtilization statistic")
        self.assertIn(('Sink', 'Sink1', 'AvgTimeInSystem'), pivot_table.index,
                      "Pivot table missing Sink AvgTimeInSystem statistic")
        self.assertIn(('Source', 'Source1', 'NumberExited'), pivot_table.index,
                      "Pivot table missing Source NumberExited statistic")


if __name__ == '__main__':
    unittest.main()
