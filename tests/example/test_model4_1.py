import unittest
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.global_imports import random
from src.core.simulation.simulation import run_simulation, run_replications


def setup_model4_1(env):
    source1 = Source(env, "Source1", (random.expovariate, 1 / 1.25))
    server1 = Server(env, "Server1", (random.expovariate, 1))
    sink1 = Sink(env, "Sink1")

    source1.connect(server1)
    server1.connect(sink1)


class TestCases(unittest.TestCase):

    def test_single_run(self):
        pivot_table = run_simulation(model=setup_model4_1, steps=1440, new_database=True)                                   # 1 day
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Value'], 4.1788)  # 6.0149?

    def test_sequential_replications(self):
        pivot_table = run_replications(model=setup_model4_1, steps=1440, num_replications=10, multiprocessing=False, new_database=True)

        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Minimum'], 2.5888)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Average'], 5.5324)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Maximum'], 8.6667)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Half-Width'], 1.2724)

    def test_parallel_replications(self):
        pivot_table = run_replications(model=setup_model4_1, steps=1440, num_replications=10, multiprocessing=False, new_database=True)

        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Minimum'], 2.5888)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Average'], 5.5324)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Maximum'], 8.6667)
        self.assertEqual(pivot_table.at[('Entity', 'Entity', 'TimeInSystem (average)'), 'Half-Width'], 1.2724)
