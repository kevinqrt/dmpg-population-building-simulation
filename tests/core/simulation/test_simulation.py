import unittest

import src.core.global_imports as gi
from src.core.simulation.simulation import run_simulation


def dummy_model(env):
    return env


class TestCases(unittest.TestCase):
    """
    Tests whether the global variable COLLECT_ENTITY_TYPE_STATS is correctly reset
    """

    def setUp(self):
        gi.COLLECT_ENTITY_TYPE_STATS = True  # intentionally activate

    def test_run_simulation_resets_collect_entity_type_stats(self):
        self.assertTrue(gi.COLLECT_ENTITY_TYPE_STATS)

        # Call the simulation
        run_simulation(model=dummy_model, steps=10)

        # Expectation: flag is reset
        self.assertFalse(gi.COLLECT_ENTITY_TYPE_STATS)
