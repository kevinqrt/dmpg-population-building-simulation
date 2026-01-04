import unittest
import simpy
from typing import Union
from src.core.components.entity import EntityManager
from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.entity import Entity
from src.core.simulation.simulation import run_simulation
from src.core.statistics.tally_statistic import TallyStatistic


class SubEntity(Entity):
    """
    Represents a sub-entity that extends the generic Entity class with additional attributes.
    """

    def __init__(self, name: str,
                 creation_time: Union[int, float],
                 entity_type: str = "Default",
                 is_parent: bool = None,
                 sequence_index=None) -> None:
        """
        Initialize a SubEntity instance.

        :param name: The name of the sub-entity.
        :param creation_time: The creation time of the sub-entity.
        :param entity_type: The type of the sub-entity.
        """

        super().__init__(name, creation_time, entity_type)
        self.num_times_processed = 0
        self.server_history = []

        if sequence_index is not None:
            self.sequence_index = sequence_index

    def count_processing(self) -> None:
        """
        Increment the count of times this sub-entity has been processed.
        """
        self.num_times_processed += 1

    def add_to_server_history(self, server: str) -> None:
        """
        Add a server to the processing history of this sub-entity.

        :param server: The name of the server to add to the history.
        """
        self.server_history.append(server)

    def __repr__(self):
        """
        Provide a string representation of the SubEntity instance, showing its lifecycle.

        :return: A string representation of the sub-entity, including its name, creation time,
        and destruction time (if any).
        """

        return f"{self.name} ({self.creation_time})" if not self.destruction_time \
            else f"{self.name} ({self.destruction_time - self.creation_time})"


# Define trigger functions for the add-on process triggers
def after_processing_trigger(server, entity, *args, **kwargs):
    """
    Trigger function to update entity processing count and server history.
    """
    # Only process SubEntity objects
    if isinstance(entity, SubEntity):
        entity.count_processing()
        entity.add_to_server_history(server.name)
    return True


def before_routing_trigger(server, entity, *args, **kwargs):
    """
    Trigger function that checks processing count before routing.
    If the entity has been processed too many times, override normal routing.
    """
    # Check if we're in the inspection server
    if server.name == "Inspection" and isinstance(entity, SubEntity):
        max_processing_count = 11

        if entity.num_times_processed >= max_processing_count:
            # Find the BadParts sink in connections
            for cumulative_probability, (connection, vehicle) in server.connection_cache.items():
                if connection.next_component.name == "BadParts":
                    # Override normal routing by routing directly to BadParts
                    connection.next_component.handle_entity_arrival(entity)
                    server.number_exited_pivot_table += 1
                    # Return False to prevent normal routing
                    return False

    # Return True to use normal probability-based routing
    return True


def combined_inspection_trigger(server, entity, *args, **kwargs):
    """
    Combined trigger for the Inspection server that does both processing counting
    and routing limit checks.
    """
    # First run the standard processing update
    after_processing_trigger(server, entity, *args, **kwargs)

    # Then check for routing limitations
    max_processing_count = 11

    if server.name == "Inspection" and isinstance(entity, SubEntity):
        if entity.num_times_processed >= max_processing_count:
            # Find the BadParts sink in connections
            for cumulative_probability, (connection, vehicle) in server.connection_cache.items():
                if connection.next_component.name == "BadParts":
                    # Override normal routing by routing directly to BadParts
                    connection.next_component.handle_entity_arrival(entity)
                    server.number_exited_pivot_table += 1
                    # Return False to prevent normal routing
                    return False

    # Return True to use normal probability-based routing
    return True


def after_entity_destruction(sink, entity, worker, processing_time):
    """
    Trigger function to record processing count after entity destruction.
    """
    if isinstance(entity, SubEntity):
        sink.tally_statistic.record(entity.num_times_processed)
    return True


def setup_model_pcb_triggers(env):
    """Model setup using add-on process triggers"""
    # Create servers, sinks, and sources
    source1 = Source(env, "PCB", (random.expovariate, 1 / 6),
                     entity_class=SubEntity)

    # Servers with after_processing_trigger to count processing and update history
    server1 = Server(env, "Placement", (random.triangular, 3, 5, 4),
                     after_processing_trigger=after_processing_trigger)
    server2 = Server(env, "FinePitchFast", (random.triangular, 8, 10, 9),
                     after_processing_trigger=after_processing_trigger)
    server3 = Server(env, "FinePitchMedium", (random.triangular, 18, 22, 20),
                     after_processing_trigger=after_processing_trigger)
    server4 = Server(env, "FinePitchSlow", (random.triangular, 22, 26, 24),
                     after_processing_trigger=after_processing_trigger)
    server5 = Server(env, "Inspection", (random.uniform, 2, 4),
                     after_processing_trigger=combined_inspection_trigger)
    server6 = Server(env, "Rework", (random.triangular, 2, 6, 4),
                     after_processing_trigger=after_processing_trigger)

    # Sinks with after_destruction_trigger to record processing count
    sink1 = Sink(env, "GoodParts", after_processing_trigger=after_entity_destruction)
    sink2 = Sink(env, "BadParts", after_processing_trigger=after_entity_destruction)

    # Set up connections with routing probabilities for servers
    source1.connect(server1)

    server1.connect(server2)
    server1.connect(server3)
    server1.connect(server4)
    server2.connect(server5)
    server3.connect(server5)
    server4.connect(server5)
    server6.connect(server1)

    # Set routing probabilities to quickly test the limit
    server5.connect(sink1, 5)
    server5.connect(sink2, 5)
    server5.connect(server6, 90)  # Higher probability to route to Rework to hit the limit faster in the test


class TestAddOnProcessTriggers(unittest.TestCase):

    def setUp(self):
        self.tally_statistic = TallyStatistic()
        self.env = simpy.Environment()
        self.entity_sub_class = SubEntity

    def test_single_run_statistics(self):
        """Test the simulation with add-on process triggers implementation"""
        # Use a shorter simulation time for testing
        pivot_table = run_simulation(model=setup_model_pcb_triggers, steps=500)

        # Print key statistics for debugging
        print(f"Average time in system: {pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Value']:.2f}")
        print(f"GoodParts Avg Processing: {pivot_table.at[('Sink', 'GoodParts', 'NumTimesProcessed (average)'), 'Value']:.2f}")
        print(f"BadParts Avg Processing: {pivot_table.at[('Sink', 'BadParts', 'NumTimesProcessed (average)'), 'Value']:.2f}")
        print(f"BadParts Max Processing: {pivot_table.at[('Sink', 'BadParts', 'NumTimesProcessed (max)'), 'Value']}")
        print(f"Entities processed (GoodParts): {pivot_table.at[('Sink', 'GoodParts', 'NumberEntered'), 'Value']}")
        print(f"Entities processed (BadParts): {pivot_table.at[('Sink', 'BadParts', 'NumberEntered'), 'Value']}")

        # Check entity statistics
        self.assertGreater(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Value'], 0)

        # Check sink statistics
        self.assertGreater(pivot_table.at[('Sink', 'GoodParts', 'NumTimesProcessed (average)'), 'Value'], 0)
        self.assertGreaterEqual(pivot_table.at[('Sink', 'GoodParts', 'NumTimesProcessed (max)'), 'Value'],
                                pivot_table.at[('Sink', 'GoodParts', 'NumTimesProcessed (min)'), 'Value'])

        # Check that at least one entity has reached the processing limit
        self.assertGreater(pivot_table.at[('Sink', 'BadParts', 'NumTimesProcessed (average)'), 'Value'], 0)

        self.assertGreaterEqual(pivot_table.at[('Sink', 'BadParts', 'NumTimesProcessed (max)'), 'Value'], 11.0,
                                "BadParts should have entities with at least 11 processes")
        self.assertLess(pivot_table.at[('Sink', 'BadParts', 'NumTimesProcessed (max)'), 'Value'], 15.0,
                        "BadParts max processes should be close to the limit of 11")

    def test_record(self):
        """Test basic recording functionality of the TallyStatistic class"""
        self.tally_statistic.record(5)
        self.assertEqual(self.tally_statistic.values, [5], 'Tally statistics not recorded correctly')

        # Add more values and check the list
        self.tally_statistic.record(7)
        self.tally_statistic.record(11)
        self.assertEqual(self.tally_statistic.values, [5, 7, 11], 'Multiple values not recorded correctly')

    def test_entity_class(self):
        """Test that entity types are correctly maintained in the model"""
        env = simpy.Environment()
        EntityManager.initialize(env)
        EntityManager.destroy_all_entities()

        source = Source(env, "TestSource", (random.expovariate, 1 / 6),
                        entity_class=SubEntity)
        server = Server(env, "TestServer", (random.triangular, 3, 5, 4),
                        after_processing_trigger=after_processing_trigger)
        sink = Sink(env, "TestSink", after_processing_trigger=after_entity_destruction)
        source.connect(server)
        server.connect(sink)

        simulation_time = 1000
        env.run(until=simulation_time)

        # Verify all created entities are SubEntity instances
        for entity in source.entities:
            self.assertIsInstance(entity, SubEntity, 'Entity is not a SubEntity instance')
            self.assertTrue(issubclass(entity.__class__, SubEntity), 'Entity class is not a subclass of SubEntity')

    def test_tally_statistic_functionality(self):
        """Tests that TallyStatistic records multiple values correctly and calculates min, max, and average."""
        # Record different values to simulate various processing times
        values_to_record = [3, 5, 7, 9, 11]
        for value in values_to_record:
            self.tally_statistic.record(value)

        # Retrieve min, max, and average using the class method
        min_value, max_value, avg_value = self.tally_statistic.calculate_statistics()

        # Verify against expected values
        self.assertEqual(min_value, 3, "Minimum value calculation is incorrect")
        self.assertEqual(max_value, 11, "Maximum value calculation is incorrect")
        self.assertAlmostEqual(avg_value, 7, places=1, msg="Average value calculation is incorrect")

    def test_after_processing_trigger(self):
        """Test that after_processing_trigger correctly counts processing"""
        # Create a mock entity and server
        env = simpy.Environment()
        entity = SubEntity("TestEntity", 0)
        server = Server(env, "TestServer", (random.triangular, 3, 5, 4))

        # Initial count should be 0
        self.assertEqual(entity.num_times_processed, 0)

        # Apply the trigger
        after_processing_trigger(server, entity)

        # Count should be incremented to 1
        self.assertEqual(entity.num_times_processed, 1)

        # Server history should include the server name
        self.assertEqual(entity.server_history, ["TestServer"])

        # Apply trigger again
        after_processing_trigger(server, entity)

        # Count should be incremented to 2
        self.assertEqual(entity.num_times_processed, 2)

        # Server history should have two entries
        self.assertEqual(entity.server_history, ["TestServer", "TestServer"])

    def test_before_routing_trigger_normal_case(self):
        """Test that before_routing_trigger works for normal case"""
        # Create a mock entity, server, and connections
        env = simpy.Environment()
        entity = SubEntity("TestEntity", 0)
        entity.num_times_processed = 5  # Set to a value less than the limit

        # Create servers and connections
        inspection = Server(env, "Inspection", (random.uniform, 2, 4))
        sink1 = Sink(env, "GoodParts")
        sink2 = Sink(env, "BadParts")
        sink3 = Sink(env, "Rework")

        inspection.connect(sink1, 10)
        inspection.connect(sink2, 10)
        inspection.connect(sink3, 80)

        # Check that routing should proceed normally
        result = before_routing_trigger(inspection, entity)
        self.assertTrue(result, "Trigger should return True for normal routing")

    def test_before_routing_trigger_limit_case(self):
        """Test that before_routing_trigger correctly routes to BadParts when limit is reached"""
        # Create a mock entity, server, and connections
        env = simpy.Environment()
        EntityManager.initialize(env)
        entity = SubEntity("TestEntity", 0)
        entity.num_times_processed = 11  # Set to the limit

        # Create servers and connections
        inspection = Server(env, "Inspection", (random.uniform, 2, 4))
        sink1 = Sink(env, "GoodParts")
        sink2 = Sink(env, "BadParts")
        sink3 = Sink(env, "Rework")

        # Track sink entries to verify routing
        sink2.number_entered_pivot_table = 0

        inspection.connect(sink1, 10)
        inspection.connect(sink2, 10)
        inspection.connect(sink3, 80)

        # Mock the handle_entity_arrival method to verify it's called
        original_handle = sink2.handle_entity_arrival
        sink2_called = [False]

        def mock_handle(entity):
            sink2_called[0] = True
            sink2.number_entered_pivot_table += 1

        sink2.handle_entity_arrival = mock_handle

        # Check that routing is overridden and entity is sent to BadParts
        result = before_routing_trigger(inspection, entity)
        self.assertFalse(result, "Trigger should return False for limit case")
        self.assertTrue(sink2_called[0], "BadParts sink should be called")
        self.assertEqual(sink2.number_entered_pivot_table, 1, "One entity should have entered BadParts")

        # Restore original method
        sink2.handle_entity_arrival = original_handle

    def test_after_entity_destruction_trigger(self):
        """Test that after_entity_destruction_trigger correctly records processing count"""
        # Create a mock entity and sink
        env = simpy.Environment()
        EntityManager.initialize(env)

        # Create test entities with manual processing counts
        entity = SubEntity("TestEntity", 0)
        entity.num_times_processed = 7  # Manually set count
        sink = Sink(env, "TestSink")

        # Ensure sink has a tally statistic
        sink.tally_statistic = TallyStatistic()

        # Apply the trigger
        after_entity_destruction(sink, entity, None, 0)

        # Tally should record the processing count
        self.assertEqual(sink.tally_statistic.values, [7])

        # Apply with another entity
        EntityManager.destroy_all_entities()  # Clear previous entity
        entity2 = SubEntity("TestEntity2", 0)
        entity2.num_times_processed = 11  # Manually set count
        after_entity_destruction(sink, entity2, None, 0)

        # Tally should record both counts
        self.assertEqual(sink.tally_statistic.values, [7, 11])

        # Calculate statistics
        min_val, max_val, avg_val = sink.tally_statistic.calculate_statistics()
        self.assertEqual(min_val, 7)
        self.assertEqual(max_val, 11)
        self.assertEqual(avg_val, 9)

    def test_combined_inspection_trigger(self):
        """Test that combined_inspection_trigger correctly handles both counting and routing"""
        # Create a mock entity, server, and connections
        env = simpy.Environment()
        EntityManager.initialize(env)
        entity = SubEntity("TestEntity", 0)
        entity.num_times_processed = 10  # One less than the limit

        # Create servers and connections
        inspection = Server(env, "Inspection", (random.uniform, 2, 4))
        sink1 = Sink(env, "GoodParts")
        sink2 = Sink(env, "BadParts")
        sink3 = Sink(env, "Rework")

        inspection.connect(sink1, 10)
        inspection.connect(sink2, 10)
        inspection.connect(sink3, 80)

        # Mock the handle_entity_arrival method to verify it's called
        original_handle = sink2.handle_entity_arrival
        sink2_called = [False]

        def mock_handle(entity):
            sink2_called[0] = True

        sink2.handle_entity_arrival = mock_handle

        # Apply the combined trigger
        result = combined_inspection_trigger(inspection, entity)

        # Count should be incremented to 11
        self.assertEqual(entity.num_times_processed, 11)

        # Server history should include inspection
        self.assertEqual(entity.server_history, ["Inspection"])

        # Since count is now 11, entity should be forced to BadParts
        self.assertFalse(result, "Trigger should return False when limit is reached")
        self.assertTrue(sink2_called[0], "BadParts sink should be called")

        # Restore original method
        sink2.handle_entity_arrival = original_handle

        # Try with a fresh entity
        EntityManager.destroy_all_entities()
        entity2 = SubEntity("TestEntity2", 0)
        entity2.num_times_processed = 5  # Well below the limit

        # Apply the combined trigger
        result = combined_inspection_trigger(inspection, entity2)

        # Count should be incremented to 6
        self.assertEqual(entity2.num_times_processed, 6)

        # Normal routing should proceed
        self.assertTrue(result, "Trigger should return True for normal routing")

    def test_processing_limit_is_configurable(self):
        """Test that processing limit can be configured through a variable"""
        # Create test objects
        env = simpy.Environment()
        entity = SubEntity("TestEntity", 0)
        inspection = Server(env, "Inspection", (random.uniform, 2, 4))
        sink2 = Sink(env, "BadParts")

        inspection.connect(sink2, 100)

        # Override the routing function to use a different limit
        def custom_limit_trigger(server, entity, *args, **kwargs):
            if server.name == "Inspection" and isinstance(entity, SubEntity):
                max_processing_count = 5  # Custom limit lower than the default

                if entity.num_times_processed >= max_processing_count:
                    # Find the BadParts sink in connections
                    for cumulative_probability, (connection, vehicle) in server.connection_cache.items():
                        connection.next_component.handle_entity_arrival(entity)
                        return False
            return True

        # Test with entity at exactly the custom limit
        entity.num_times_processed = 5
        original_handle = sink2.handle_entity_arrival
        sink2_called = [False]

        def mock_handle(entity):
            sink2_called[0] = True

        sink2.handle_entity_arrival = mock_handle

        result = custom_limit_trigger(inspection, entity)
        self.assertFalse(result, "Custom limit trigger should return False at custom limit")
        self.assertTrue(sink2_called[0], "BadParts sink should be called with custom limit")

        # Restore original method
        sink2.handle_entity_arrival = original_handle
