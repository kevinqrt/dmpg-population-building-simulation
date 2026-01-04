import simpy
import unittest
from src.core.components.entity import Entity, EntityManager
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.utils.helper import validate_probabilities
from src.core.types.queue_type import QueueType


class TestCases(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_entity_initialization(self):
        # Test the initialization of an Entity object
        entity = Entity("TestEntity", 10)

        self.assertEqual(entity.name, "TestEntity", "Name is not correctly assigned")
        self.assertEqual(entity.creation_time, 10, "Creation time is not correctly assigned")
        self.assertIsNone(entity.destruction_time, "Destruction time should initially be None")

    def test_source_initialization(self):
        # Test the initialization of a Source object
        source = Source(self.env, "TestSource")
        assert source.env == self.env  # Check if environment is correctly assigned
        assert source.name == "TestSource"  # Check if name is correctly assigned
        assert len(source.next_components) == 0  # Next servers list should initially be empty

    def test_server_initialization(self):
        # Test the initialization of a Server object
        server = Server(self.env, "TestServer")
        assert server.env == self.env  # Check if environment is correctly assigned
        assert server.name == "TestServer"  # Check if name is correctly assigned
        assert server.queuing_order == QueueType.FIFO  # Default queue order should be FIFO

    def test_sink_initialization(self):
        # Test the initialization of a Sink object
        sink = Sink(self.env, "TestSink")
        assert sink.env == self.env  # Check if environment is correctly assigned
        assert sink.name == "TestSink"  # Check if name is correctly assigned

    def test_entity_reset_all(self):
        # Test the reset_all class method of Entity
        Entity("Entity1", 10)
        Entity("Entity2", 20)
        EntityManager.destroy_all_entities()
        assert len(EntityManager.entities) == 0  # Check if all entities are cleared

    def test_source_connect(self):
        # Test the connect method of Source
        source = Source(self.env, "TestSource")
        server = Server(self.env, "TestServer")
        source.connect(server)
        assert len(source.next_components) == 1  # Check if server is correctly connected

    def test_source_validate_probabilities(self):
        # Test the validate_probabilities method of Source
        source = Source(self.env, "TestSource")
        server1 = Server(self.env, "Server1")
        server2 = Server(self.env, "Server2")

        source.connect(server1, 70)
        source.connect(server2, 30)
        validate_probabilities(source)

        # Check if probabilities sum up to 100
        assert sum(prob for _, prob, _, _ in source.next_components) == 100, "Probabilities do not sum to 100"
