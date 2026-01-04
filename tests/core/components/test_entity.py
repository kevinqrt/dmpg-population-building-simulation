import random
import unittest

import simpy

from src.core.components.entity import EntityManager
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source


class TestCase(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_entity_lifecycle(self):
        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6))
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4))
        sink = Sink(self.env, "TestSink")
        source.connect(server)
        server.connect(sink)

        simulation_time = 1000
        self.env.run(until=simulation_time)

        for entity in source.entities:
            # Check if entity has been created
            assert entity.creation_time is not None
