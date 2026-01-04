import unittest
import simpy
from src.core.types.queue_type import QueueType
from src.core.global_imports import random
from src.core.components.entity import EntityManager
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.components.logistic.storage import Storage
from src.core.components.logistic.storage_manager import StorageManager


class TestCases(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

        # setup StorageManager
        StorageManager.add_storage_queue('test_queue')
        StorageManager.env = self.env

    def test_storage_reset(self):
        def test_storage_1(entity):
            return 'test_queue'

        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6))
        storage = Storage(self.env, "TestStorage",
                          processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4),
                          storage_expression=(test_storage_1, 'number_entered_pivot_table'))
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4), storage_queue='test_queue')
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        storage.reset()

        # Check if entity has been stored and released
        assert storage.number_entered_pivot_table == 0

    def test_storage_store_entity(self):
        def test_storage_1(entity):
            return 'test_queue'

        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6))
        storage = Storage(self.env, "TestStorage", storage_expression=(test_storage_1,), processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4))
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(sink)
        simulation_time = 1000
        self.env.run(until=simulation_time)

        # Check if entity has been stored
        assert len(StorageManager.storage_queues['test_queue'],) == 1

    def test_storage_capicity(self):
        def test_storage_1(entity):
            return 'test_queue'

        def fix_time():
            return 1

        source = Source(self.env, "TestSource", (fix_time,))
        storage = Storage(self.env, "TestStorage", storage_expression=(test_storage_1,), capacity=2, processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4))
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(sink)
        simulation_time = 1000
        self.env.run(until=simulation_time)

        # Check if entity has been stored
        assert len(StorageManager.storage_queues['test_queue'],) == 2

    def test_storage_and_relase_queue_based(self):
        def test_storage_1(entity):
            return 'test_queue'

        def fix_time():
            return 1

        source = Source(self.env, "TestSource", (fix_time,))
        storage = Storage(self.env, "TestStorage", processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4),
                          storage_expression=(test_storage_1,),)
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4), storage_queue='test_queue')
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        # Check if entity has been stored and released
        assert server.number_entered_pivot_table > 0

    def test_storage_and_relase_time_based(self):

        def fix_time():
            return 1

        source = Source(self.env, "TestSource", (fix_time,))
        storage = Storage(self.env, "TestStorage", processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4))
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4), storage_queue='test_queue')
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        # Check if entity has been stored and released
        assert server.number_entered_pivot_table > 0

    def test_storage_and_relase_queue_LIFO_entity(self):
        def test_storage_1(entity):
            return 'test_queue'

        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6))
        storage = Storage(self.env, "TestStorage", queuing_order=QueueType.LIFO,
                          processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4),
                          storage_expression=(test_storage_1,), )
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4), storage_queue='test_queue')
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        # Check if entity has been stored and released
        assert server.number_entered_pivot_table > 1

    def test_storage_and_relase_queue_entity_with_entity_list(self):
        def test_storage_1(entity):
            return 'test_queue'

        def fix_time():
            return 1

        entity_list = {'Default': (fix_time,)}

        source = Source(self.env, "TestSource", (fix_time,))
        storage = Storage(self.env, "TestStorage",
                          entity_processing_times=entity_list,
                          processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4),
                          storage_expression=(test_storage_1,), )
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4), storage_queue='test_queue')
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        # Check if entity has been stored and released
        assert server.number_entered_pivot_table > 1

    def test_storage_and_relase_queue_entity_with_global_entity_list(self):
        def test_storage_1(entity):
            return 'test_queue'

        def fix_time():
            return 1

        global_entity_list = {'TestStorage': {'Default': (fix_time,)}}

        source = Source(self.env, "TestSource", (fix_time,))
        storage = Storage(self.env, "TestStorage",
                          processing_time_distribution_with_parameters=(random.triangular, 3, 5, 4),
                          global_processing_times=global_entity_list,
                          storage_expression=(test_storage_1,), )
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4), storage_queue='test_queue')
        sink = Sink(self.env, "TestSink")
        source.connect(storage)
        storage.connect(server)
        server.connect(sink)
        simulation_time = 10000
        self.env.run(until=simulation_time)

        # Check if entity has been stored and released
        assert server.number_entered_pivot_table > 1

    def test_representation(self):
        def test_storage_1(entity):
            return 'test_queue'

        storage = Storage(self.env, "TestStorage", storage_expression=(test_storage_1,))
        storage_name = storage.__repr__()

        assert storage_name == storage.name
