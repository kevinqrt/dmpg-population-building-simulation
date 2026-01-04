import simpy
import unittest
from src.core.components.entity import Entity, EntityManager
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.global_imports import random
from src.core.types.queue_type import QueueType


class TestCase(unittest.TestCase):

    def setUp(self):
        """Set up a SimPy environment and mock Server for testing processing times."""
        self.env = simpy.Environment()
        EntityManager.env = self.env

        self.default_processing_time = (lambda: 5,)  # Default processing time for Server
        self.entity_processing_times = {
            'TypeA': (lambda: 10,),  # Entity-specific processing time for TypeA
            'TypeB': (lambda: 15,)
        }
        self.global_processing_times = {
            'TestServer': {'TypeC': (lambda: 20,)}  # Global time for TypeC specific to this server
        }
        self.server = Server(
            env=self.env,
            name="TestServer",
            processing_time_distribution_with_parameters=self.default_processing_time,
            capacity=1,
            entity_processing_times=self.entity_processing_times,
            global_processing_times=self.global_processing_times,
            queuing_order=QueueType.FIFO
        )

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

    def test_server_processing_time(self):
        server = Server(self.env, "TestServer",
                        processing_time_distribution_with_parameters=(random.uniform, 5, 10))

        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        entity = Entity("TestEntity", 0)
        server.handle_entity_arrival(entity)
        self.env.run(until=20)

        # Check if the entity processing time is within the expected range

        self.assertTrue(5 <= server.total_processing_time_pivot_table <= 10,
                        "Server processing time is outside the expected range")

    def test_server_queue_management(self):
        # Initialize server with a small but non-zero capacity
        server = Server(self.env, "TestServer", queuing_order="FIFO", capacity=1)

        # Add entities to the server's queue without processing them
        for i in range(5):
            entity = Entity(f"Entity{i}", i)
            server.handle_entity_arrival(entity)

        # Verify if entities are queued in FIFO order
        for i, (entity, _) in enumerate(server.input_queue):
            self.assertEqual(entity.name, f"Entity{i}", f"{entity.name} != Entity{i}")

    def test_server_fifo_queue_management(self):
        server = Server(self.env, "TestServer",
                        processing_time_distribution_with_parameters=(random.uniform, 1, 5),
                        queuing_order="FIFO")
        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        for i in range(3):
            server.handle_entity_arrival(Entity(f"Entity{i}", i))
        self.env.run(until=30)

        self.assertEqual(server.total_entities_processed_pivot_table, 3, "Server did not process all entities")

    def test_end_to_end_workflow(self):
        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6))
        server = Server(self.env, "TestServer", (random.triangular, 3, 5, 4))
        sink = Sink(self.env, "TestSink")

        source.connect(server)
        server.connect(sink)

        self.env.run(until=1000)

        # Check if at least one entity has been created, processed, and reached the sink.
        self.assertGreater(len(source.entities), 0, "No entities were created by the source")
        self.assertGreater(server.total_entities_processed_pivot_table, 0, "No entities were processed by the server")
        self.assertGreater(sink.entities_processed, 0, "No entities were processed by the sink")

    def test_server_processing_multiple_entities(self):
        server = Server(self.env, "TestServerMulti", (random.uniform, 1, 2))
        sink = Sink(self.env, "TestSinkMulti")
        server.connect(sink, 100)

        for i in range(5):
            server.handle_entity_arrival(Entity(f"MultiEntity{i}", i))
        self.env.run(until=15)

        self.assertEqual(server.total_entities_processed_pivot_table, 5, "Server did not process all entities correctly")

    def test_server_capacity_with_single_entity(self):
        server = Server(self.env, "ServerCapacity2", capacity=1,
                        processing_time_distribution_with_parameters=(lambda: 2,))
        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        entity = Entity("Entity1", self.env.now)
        server.handle_entity_arrival(entity)
        self.env.run(until=2.0001)

        # Test the server's behavior when processing a single entity
        # ensuring the capacity feature does not affect the expected processing of individual entities.
        self.assertIsNot(entity.destruction_time, None,
                         "Server did not process the entity within the expected timeframe")
        self.assertEqual(entity.destruction_time, 2, "Entity processing time does not match expected")

    def test_server_capacity_with_two_entities(self):
        server = Server(self.env, "ServerCapacity2", capacity=2,
                        processing_time_distribution_with_parameters=(lambda: 2,))
        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        entity = Entity("Entity1_cap2", self.env.now)
        server.handle_entity_arrival(entity)

        entity2 = Entity("Entity2_cap2", self.env.now)
        server.handle_entity_arrival(entity2)

        self.env.run(until=2.0001)

        # Test the server's behavior when processing a single entity
        # ensuring the capacity feature does not affect the expected processing of individual entities.
        self.assertIsNot(entity2.destruction_time, None,
                         "Server did not process the entity within the expected timeframe")
        self.assertEqual(entity2.destruction_time, 2, "Entity processing time does not match expected")

    def test_server_capacity_exceeded(self):
        server = Server(self.env, "ServerCapacity1", capacity=1,
                        processing_time_distribution_with_parameters=(lambda: 2,))
        sink = Sink(self.env, "TestSink")
        server.connect(sink)
        entities = [Entity(f"Entity{i + 1}", self.env.now) for i in range(3)]
        for entity in entities:
            server.handle_entity_arrival(entity)
        self.env.run(until=5)

        # Evaluate the server's ability to queue entities when its processing capacity is exceeded
        # and verify entities are processed according to the server's capacity
        self.assertTrue(all(entity.destruction_time is not None for entity in entities[:2]),
                        "Not all entities were processed as expected")
        self.assertIsNone(entities[2].destruction_time, "Server processed more entities than its capacity")

    def test_server_reset_with_capacity(self):
        server = Server(self.env, "ServerCapacity4", capacity=1,
                        processing_time_distribution_with_parameters=(lambda: 5,))
        sink = Sink(self.env, "TestSink")
        server.connect(sink)
        entities = [Entity(f"Entity{i + 1}", self.env.now) for i in range(2)]
        for entity in entities:
            server.handle_entity_arrival(entity)

        # Reset all servers
        Server.servers.reset_all()
        self.env.run(until=3)

        # Ensure that resetting the server clears both the queue and active processing slots
        self.assertEqual(len(server.input_queue), 0, "Server did not clear its queue upon reset")
        self.assertEqual(len(server.resource.users), 0, "Server did not clear its active processing slots upon reset")
        self.assertEqual(server.total_entities_processed_pivot_table, 0, "Server did not reset its processed entities count")

    def test_server_processing_with_capacity(self):
        """
        This test revealed a problem with the new routing implementation.
        When trying to route multiple Entities at the same time, only one is routed.
        """
        Sink.store_processed_entities = True

        server = Server(self.env, "ServerOrderTime", (random.uniform, 1.99999999, 2.00000001), capacity=2)
        sink = Sink(self.env, "TestSink")
        server.connect(sink)

        # Create and process multiple entities
        entities = [Entity(f"EntityOrderTime{i + 2}", self.env.now) for i in range(4)]
        for entity in entities:
            server.handle_entity_arrival(entity)

        self.env.run(until=4.01)

        # test if the server processes entities in the correct order: FIFO
        # and calculates the processing time correctly when multiple entities are involved
        processed_entities_names = [entity.name for entity in sink.processed_entities]
        expected_order = [entity.name for entity in entities]

        self.assertEqual(len(expected_order), len(processed_entities_names), "Entities were not processed as expected.")

    def test_default_processing_time(self):
        """Test that the default processing time is used when no specific time is set."""
        entity = Entity(name="Entity1", creation_time=0)  # Not in entity-specific or global settings
        processing_time = self.server._determine_processing_time(entity)
        self.assertEqual(processing_time[0](), 5)

    def test_entity_specific_processing_time(self):
        """Test that entity-specific processing time is used when available."""
        entity = Entity(name="Entity2", creation_time=0, entity_type='TypeA')
        processing_time = self.server._determine_processing_time(entity)
        self.assertEqual(processing_time, self.entity_processing_times['TypeA'])

    def test_global_processing_time(self):
        """Test that global processing time is used when no entity-specific time is available."""
        entity = Entity(name="Entity3", creation_time=0, entity_type='TypeC')
        processing_time = self.server._determine_processing_time(entity)
        self.assertEqual(processing_time, self.global_processing_times['TestServer']['TypeC'])

    def test_preference_order_entity_specific_over_global(self):
        """Test that entity-specific time takes precedence over global time."""
        entity = Entity(name="Entity4", creation_time=0, entity_type='TypeA')  # Exists in both entity and global settings
        processing_time = self.server._determine_processing_time(entity)
        self.assertEqual(processing_time, self.entity_processing_times['TypeA'])

    def test_preference_order_global_over_default(self):
        """Test that global time takes precedence over the default time."""
        entity = Entity(name="Entity5", creation_time=0,
                        entity_type='TypeC')  # Exists only in global settings for this server
        processing_time = self.server._determine_processing_time(entity)
        self.assertEqual(processing_time, self.global_processing_times['TestServer']['TypeC'])
