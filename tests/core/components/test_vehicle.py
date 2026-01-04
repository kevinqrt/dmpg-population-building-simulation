import random
import unittest

import simpy

from src.core.components.vehicle import Vehicle
from src.core.components.vehicle_manager import VehicleManager
from src.core.components.entity import EntityManager
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source


class TestCase(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_two_vehicle_transport_entity(self):
        vehicle_1 = Vehicle(self.env, 'test_vehicle_1', (lambda: 20,))
        vehicle_2 = Vehicle(self.env, 'test_vehicle_2', (lambda: 20,))
        VehicleManager().env = self.env

        source1 = Source(self.env, "TestSource_1", (random.expovariate, 1 / 6))
        source2 = Source(self.env, "TestSource_2", (random.expovariate, 1 / 6))
        server1 = Server(self.env, "TestServer_1", (random.triangular, 3, 5, 4), vehicle_group="DefaultVehicleGroup")
        server2 = Server(self.env, "TestServer_2", (random.triangular, 3, 5, 4), vehicle_group="DefaultVehicleGroup")
        sink = Sink(self.env, "TestSink")
        source1.connect(server1)
        source2.connect(server2)
        server1.connect(sink)
        server2.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        self.assertGreater(server1.number_entered_pivot_table, 10)
        self.assertGreater(server2.number_entered_pivot_table, 10)
        self.assertGreater(vehicle_1.entities_transported, 10)
        self.assertGreater(vehicle_2.entities_transported, 10)

    def test_custom_vehicle_group_for_transport_entity(self):
        VehicleManager().add_vehicle_group('Test')
        VehicleManager().env = self.env
        vehicle = Vehicle(self.env, 'test_vehicle', (lambda: 2,), vehicle_group='Test')

        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6), vehicle_group='Test')
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4))
        sink = Sink(self.env, "TestSink")
        source.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        self.assertGreater(vehicle.entities_transported, 10)
        self.assertGreater(server.number_entered_pivot_table, 10)

    def test_custom_vehicle_group_with_strategy_for_transport_entity(self):
        VehicleManager().add_vehicle_group('Test', strategy=(lambda vehicle_group, calling_object, entity, destination: vehicle_group[0],))
        VehicleManager().env = self.env
        vehicle_1 = Vehicle(self.env, 'test_vehicle_1', (lambda: 20,), vehicle_group='Test')
        vehicle_2 = Vehicle(self.env, 'test_vehicle_2', (lambda: 20,), vehicle_group='Test')

        source1 = Source(self.env, "TestSource_1", (random.expovariate, 1 / 6))
        source2 = Source(self.env, "TestSource_2", (random.expovariate, 1 / 6))
        server1 = Server(self.env, "TestServer_1", (random.triangular, 3, 5, 4), vehicle_group="Test")
        server2 = Server(self.env, "TestServer_2", (random.triangular, 3, 5, 4), vehicle_group="Test")
        sink = Sink(self.env, "TestSink")
        source1.connect(server1)
        source2.connect(server2)
        server1.connect(sink)
        server2.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        self.assertGreater(server1.number_entered_pivot_table, 10)
        self.assertGreater(server2.number_entered_pivot_table, 10)
        self.assertGreater(vehicle_1.entities_transported, 10)
        self.assertEqual(vehicle_2.entities_transported, 0)
