import simpy
import unittest
from src.core.components.entity import Entity, EntityManager
from src.core.components.sink import Sink


class TestCase(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_sink_reset(self):
        # Test the reset method of Sink
        sink = Sink(self.env, "TestSink")
        sink.entities_processed = 4
        sink.reset()
        self.assertEqual(sink.entities_processed, 0, "entities_processed was not resetted to 0")

    def test_sink_process_entity(self):
        # Test the process_entity method of Sink
        sink = Sink(self.env, "TestSink")
        entity = Entity("TestEntity", 10)
        sink.handle_entity_arrival(entity)
        self.env.run(until=100)
        self.assertEqual(sink.entities_processed, 1, "Entity was not processed")
