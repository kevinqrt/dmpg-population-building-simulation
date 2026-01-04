import unittest

import src.core.global_imports as gi
from src.core.simulation.simulation import run_replications


def dummy_model(env):
    return env


class TestCases(unittest.TestCase):
    """
    Tests whether the global variable COLLECT_ENTITY_TYPE_STATS is correctly reset
    """

    def setUp(self):
        gi.COLLECT_ENTITY_TYPE_STATS = True  # intentionally activate

    def test_run_replications_resets_collect_entity_type_stats(self):
        gi.COLLECT_ENTITY_TYPE_STATS = True  # set it again
        self.assertTrue(gi.COLLECT_ENTITY_TYPE_STATS)

        # Call the replication
        run_replications(model=dummy_model, steps=10, num_replications=3)

        # Expectation: flag is reset
        self.assertFalse(gi.COLLECT_ENTITY_TYPE_STATS)
