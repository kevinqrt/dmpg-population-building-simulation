import os
import unittest
import pandas as pd
from pathlib import Path

from src.core.components.entity import EntityManager
from src.core.components.model import Model
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
import simpy
from src.core.simulation.simulation import run_simulation
from src.core.global_imports import random


def routing_smallest_queue(routing_object, entity, *parameters):
    smallest_queue = 999_999
    next_server_via = None
    for connection in routing_object.connections:
        if len(routing_object.connections[connection].next_component.input_queue) < smallest_queue:
            smallest_queue = len(routing_object.connections[connection].next_component.input_queue)
            next_server_via = routing_object.connections[connection]
    next_server_via.handle_entity_arrival(entity)


def setup_model_with_processing_durations(env):
    source1 = Source(env, "Source1", (random.expovariate, 1 / 1.25))
    server1 = Server(env, "Server1", (random.expovariate, 1))
    sink1 = Sink(env, "Sink1")

    source1.connect(server1, process_duration=0.1)
    server1.connect(sink1, process_duration=0.2)


def setup_model_without_processing_durations(env):
    source1 = Source(env, "Source1", (random.expovariate, 1 / 1.25))
    server1 = Server(env, "Server1", (random.expovariate, 1))
    sink1 = Sink(env, "Sink1")

    source1.connect(server1, process_duration=0)
    server1.connect(sink1, process_duration=0)


def setup_model_with_routing_expression(env):
    source1 = Source(env, "Source1", (random.expovariate, 1 / 1.25), routing_expression=(routing_smallest_queue,))
    server1 = Server(env, "Server1", (random.expovariate, 0.3))
    server2 = Server(env, "Server2", (random.expovariate, 1))
    sink1 = Sink(env, "Sink1")

    source1.connect(server1)
    source1.connect(server2)
    server1.connect(sink1)
    server2.connect(sink1)


class TestCases(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

        test_dir = Path(__file__).resolve().parent.parent.parent
        self.routing_table_path = os.path.join(test_dir, 'test_data/test_routing_table.csv')
        self.routing_table_with_group_path = os.path.join(test_dir, 'test_data/test_routing_table_with_group.csv')

    def tearDown(self):
        Model().reset_simulation()

    def test_connection(self):
        source = Source(self.env, "TestSource")
        server = Server(self.env, "TestServer")
        source.connect(server)
        assert len(source.connections) == 1  # Check if server is correctly connected

    def test_routing_object_connection(self):
        source = Source(self.env, "TestSource")
        server = Server(self.env, "TestServer")
        source.connect(server, process_duration=10)
        self.assertEqual(source.connections['TestServer'].process_duration, 10)
        self.assertEqual(source.connections['TestServer'].next_component.name, 'TestServer')
        self.assertEqual(source.connections['TestServer'].origin_component.name, 'TestSource')

    def test_single_run_with_processing_time(self):
        EntityManager.destroy_all_entities()
        pivot_table = run_simulation(model=setup_model_with_processing_durations, steps=1440)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Value'], 4.6185)
        # TBC: previous value 152.699 - after routing to single entities changed

    def test_single_run_with_processing_time_set_zero(self):
        EntityManager.destroy_all_entities()
        pivot_table = run_simulation(model=setup_model_without_processing_durations, steps=1440, new_database=True)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Value'], 4.1788)

    def test_single_run_route_smallest_queue(self):
        EntityManager.destroy_all_entities()
        # AvgTimeProcessing to be changed after server reset implementation
        pivot_table = run_simulation(model=setup_model_with_routing_expression, steps=1440, new_database=True)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Value'], 4.1928)
        self.assertAlmostEqual(pivot_table.at[('Server', 'Server1', 'TimeProcessing (average)'), 'Value'], 3.4969)
        self.assertEqual(pivot_table.at[('Server', 'Server2', 'TimeProcessing (average)'), 'Value'], 1.0351)

    def test_use_sequence_routing_with_dataframe(self):
        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6), sequence_routing=True)
        server_1 = Server(self.env, "TestServer1", (random.expovariate, 1 / 6), sequence_routing=True)
        server_2 = Server(self.env, "TestServer2", (random.expovariate, 1 / 6), sequence_routing=True)
        sink = Sink(self.env, "TestSink")

        source.connect(server_1)
        source.connect(server_2)

        server_1.connect(sink)
        server_2.connect(sink)

        simulation_time = 10000

        routes = {'destination': ['TestServer2', 'TestSink']}
        routing_table = pd.DataFrame(routes)
        Model().add_routing_table('destination', routing_table)

        self.env.run(until=simulation_time)

        # Check that only server 2 got entities
        assert server_1.total_entities_processed_pivot_table == 0 and server_2.total_entities_processed_pivot_table > 0

    def test_use_sequence_routing_with_file(self):
        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6), sequence_routing=True)
        server_1 = Server(self.env, "TestServer1", (random.expovariate, 1 / 6), sequence_routing=True)
        server_2 = Server(self.env, "TestServer2", (random.expovariate, 1 / 6), sequence_routing=True)
        sink = Sink(self.env, "TestSink")

        source.connect(server_1)
        source.connect(server_2)

        server_1.connect(sink)
        server_2.connect(sink)

        simulation_time = 10000

        Model().add_routing_table('destination', routing_table_file=self.routing_table_path)

        self.env.run(until=simulation_time)

        # Check that only server 2 got entities
        assert server_1.total_entities_processed_pivot_table == 0 and server_2.total_entities_processed_pivot_table > 0

    def test_creating_routing_group(self):
        Model().add_routing_group('TestGroup')
        self.assertEqual(len(Model().routing_group['TestGroup']), 0)
        self.assertIn('TestGroup', Model().routing_group)

    def test_add_member_to_routing_group(self):
        Model().add_routing_group('TestGroup')
        Model().add_member_to_group('TestGroup', 'TestServer1')

        self.assertEqual(len(Model().routing_group['TestGroup']), 1)
        self.assertIn('TestGroup', Model().routing_group)

    def test_is_group_true(self):
        Model().add_routing_group('TestGroup')
        test_value = Model().is_group('TestGroup')

        true_value = True
        assert true_value == test_value

    def test_is_group_false(self):
        test_value = Model().is_group('TestGroup')

        true_value = False
        assert true_value == test_value

    def test_use_sequence_routing_with_group(self):
        Model().add_routing_group('TestGroup')
        Model().add_member_to_group('TestGroup', 'TestServer1')
        Model().add_member_to_group('TestGroup', 'TestServer2')

        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6), sequence_routing=True)
        server_1 = Server(self.env, "TestServer1", (random.expovariate, 1 / 6), sequence_routing=True)
        server_2 = Server(self.env, "TestServer2", (random.expovariate, 1 / 6), sequence_routing=True)
        server_3 = Server(self.env, "TestServer3", (random.expovariate, 1 / 6), sequence_routing=True)
        sink = Sink(self.env, "TestSink")

        source.connect(server_1)
        source.connect(server_2)
        source.connect(server_3)

        server_1.connect(sink)
        server_2.connect(sink)
        server_3.connect(sink)

        simulation_time = 10000

        Model().add_routing_table('destination', routing_table_file=self.routing_table_with_group_path)

        self.env.run(until=simulation_time)

        assert server_1.total_entities_processed_pivot_table > 0
        assert server_2.total_entities_processed_pivot_table > 0
        assert server_3.total_entities_processed_pivot_table == 0
