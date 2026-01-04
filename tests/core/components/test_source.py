import unittest
from pathlib import Path
from typing import Union
import os
import simpy
from src.core.simulation.simulation import run_simulation

from src.core.components.entity import Entity, EntityManager
from src.core.components.sink import Sink
from src.core.components.source import Source


class TestCase(unittest.TestCase):
    entites_seen_weight_test = []
    entites_seen_arrival_table_test = []

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

        test_dir = Path(__file__).resolve().parent.parent.parent
        self.arrival_table_path_arrival_para = os.path.join(test_dir, f'test_data{os.sep}arrivalTableParameterTest.csv')
        self.arrival_table_config_path = os.path.join(test_dir, f'test_data{os.sep}arrivalTableConfigTest.csv')
        self.arrival_table_entity_test_path = os.path.join(test_dir, f'test_data{os.sep}arrivalTableEntityTest.csv')

    def test_source_reset(self):
        # Test the reset method of Source
        source = Source(self.env, "TestSource")
        source.entities_created_pivot_table = 5
        source.reset()
        self.assertEqual(source.entities_created_pivot_table, 0, "entities_created was not resetted to 0")
        self.assertEqual(len(source.entities), 0, "entities list was not cleared")

    def test_source_arrival_table_with_parameter(self):
        class TestEntity(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], test_att=None):
                super().__init__(name, creation_time)
                self.test_parameter = test_att

        source = Source(
            self.env,
            "TestSource",
            entity_class=TestEntity,
            arrival_table_file=self.arrival_table_path_arrival_para,
        )

        sink = Sink(self.env, "TestSink")
        source.connect(sink)
        simulation_time = 10
        self.env.run(until=simulation_time)
        self.assertEqual(sink.number_entered_pivot_table, 2)

    def test_source_arrival_table(self):
        class TestEntity(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], test_att=None):
                super().__init__(name, creation_time)
        source = Source(self.env, entity_class=TestEntity, name="TestSource", arrival_table_file=self.arrival_table_path_arrival_para)
        sink = Sink(self.env, "TestSink")
        source.connect(sink)
        simulation_time = 1000
        self.env.run(until=simulation_time)
        self.assertEqual(sink.number_entered_pivot_table, 3)

    def test_source_arrival_table_with_config(self):
        source = Source(
            self.env,
            "TestSource",
            arrival_table_file=self.arrival_table_config_path,
            arrival_table_config={'sep': ';', 'decimal': ','}
        )
        self.assertEqual(source.arrival_table.at[0, 'test_att'], 1.0)
        self.assertEqual(source.arrival_table.at[1, 'test_att'], 1.2)
        self.assertEqual(source.arrival_table.at[2, 'test_att'], 1.3)

    def test_source_max_arrival(self):
        def constant_time():
            return 0

        source = Source(self.env, "TestSource",
                        creation_time_distribution_with_parameters=(constant_time,),
                        max_arrival=100)
        sink = Sink(self.env, "TestSink")
        source.connect(sink)
        simulation_time = 1000
        self.env.run(until=simulation_time)
        self.assertEqual(sink.number_entered_pivot_table, 100)

    def test_weighted_source(self):
        class TestWood(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], entity_type, is_parent=False, sequence_index=None):
                super().__init__(name, creation_time)

        class TestStone(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], entity_type, is_parent=False, sequence_index=None):
                super().__init__(name, creation_time)

        def constant_time():
            return 1

        entities_seen = []

        def after_processing(sink, entity, worker, processing_time):
            entities_seen.append(entity)

        test_dict = {TestWood: 0.5, TestStone: 0.5}

        def model(env):
            source = Source(
                env,
                "TestSource",
                creation_time_distribution_with_parameters=(constant_time,),
                entity_class=test_dict,
            )
            sink = Sink(env, "TestSink", after_processing_trigger=(after_processing,))
            source.connect(sink)

        run_simulation(
            model=model,
            steps=100,
        )

        # count how many of each entity were processed
        count_wood = sum(isinstance(e, TestWood) for e in entities_seen)
        count_stone = sum(isinstance(e, TestStone) for e in entities_seen)

        self.assertEqual(count_wood, 51)
        self.assertEqual(count_stone, 49)

    def test_weighted_source_error(self):
        class TestWood(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], entity_type, is_parent=False, sequence_index=None):
                super().__init__(name, creation_time)

        class TestStone(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], entity_type, is_parent=False, sequence_index=None):
                super().__init__(name, creation_time)

        def constant_time():
            return 1

        test_dict = {TestWood: 0.1,
                     TestStone: 0.5}

        with self.assertRaises(ValueError):
            source = Source(self.env, "TestSource", creation_time_distribution_with_parameters=(constant_time,), entity_class=test_dict)
            sink = Sink(self.env, "TestSink")
            source.connect(sink)
            simulation_time = 100
            self.env.run(until=simulation_time)

    def test_source_arrival_table_with_different_entities(self):
        class TestWood(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], entity_type: str = 'Default', is_parent=False, sequence_index=None):
                super().__init__(name, creation_time)

        class TestStone(Entity):
            def __init__(self, name: str, creation_time: Union[int, float], entity_type: str = 'Default', is_parent=False, sequence_index=None):
                super().__init__(name, creation_time)

        def after_processing(sink, entity, worker, processing_time):
            from tests.core.components.test_source import TestCase
            TestCase.entites_seen_arrival_table_test.append(entity)

        source = Source(
            self.env,
            "TestSource",
            entity_class=[TestWood, TestStone],
            entity_class_column_name='entity_type',
            arrival_table_file=self.arrival_table_entity_test_path,
        )

        sink = Sink(self.env, "TestSink", after_processing_trigger=(after_processing,))
        source.connect(sink)
        simulation_time = 30
        self.env.run(until=simulation_time)

        count_wood = 0
        count_stone = 0

        from tests.core.components.test_source import TestCase
        for entity in TestCase.entites_seen_arrival_table_test:
            if type(entity) is TestWood:
                count_wood += 1

            if type(entity) is TestStone:
                count_stone += 1

        self.assertEqual(count_wood, 2)
        self.assertEqual(count_stone, 1)
