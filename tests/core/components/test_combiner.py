import unittest
import random

import simpy

from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.components.entity import EntityManager
from src.core.components.combiner import Combiner
from src.core.components.separator import Separator


class TestCases(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_combiner_separator(self):
        def fix_time():
            return 0

        source1 = Source(self.env, "TestSource1", (random.expovariate, 1 / 6), is_parent_source=True)
        source2 = Source(self.env, "TestSource2", (random.expovariate, 1 / 6), is_parent_source=False)
        combiner = Combiner(self.env, "TestCombiner", (fix_time,))
        separator = Separator(self.env, "TestSeperator", (fix_time,))

        sink = Sink(self.env, "TestSink")

        source1.connect(combiner)
        source2.connect(combiner)
        combiner.connect(separator)
        separator.connect(sink)

        simulation_time = 1000

        self.env.run(until=simulation_time)

        assert combiner.number_combinded_exited_pivot_table <= combiner.number_members_entered_pivot_table
        assert separator.number_members_exited_pivot_table > 0
        assert separator.number_parents_exited_pivot_table > 0

    def test_combiner_separator_with_rules(self):
        def fix_time():
            return 0

        combiner_rules = {
            'test_entity_1': 1,
            'test_entity_2': 2,
        }

        source1 = Source(self.env, "TestSource1", (random.expovariate, 1 / 6), is_parent_source=True)
        source2 = Source(self.env, "TestSource2", (random.expovariate, 1 / 6), is_parent_source=False, entity_type='test_entity_1')
        source3 = Source(self.env, "TestSource2", (random.expovariate, 1 / 6), is_parent_source=False, entity_type='test_entity_2')
        combiner = Combiner(self.env, "TestCombiner", (fix_time,), combination_rules=combiner_rules)
        separator = Separator(self.env, "TestSeperator", (fix_time,))

        sink = Sink(self.env, "TestSink")

        source1.connect(combiner)
        source2.connect(combiner)
        source3.connect(combiner)
        combiner.connect(separator)
        separator.connect(sink)

        simulation_time = 1000

        self.env.run(until=simulation_time)

        assert combiner.number_combinded_exited_pivot_table <= combiner.number_members_entered_pivot_table
        assert separator.number_members_exited_pivot_table > 0
        assert separator.number_parents_exited_pivot_table > 0
