from core.components.date_time import DateTime
from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_replications


def setup_model5_1(env):
    source = Source(env, "Source", (random.expovariate, 1 / 6))
    placement = Server(env, "Placement", (random.triangular, 3, 5, 4))
    inspection = Server(env, "Inspection", (random.uniform, 2, 4))
    good_parts = Sink(env, "Goodparts")
    bad_parts = Sink(env, "Badparts")

    source.connect(placement)
    placement.connect(inspection)
    inspection.connect(good_parts, 92)
    inspection.connect(bad_parts, 8)


def main():
    run_replications(model=setup_model5_1, steps=DateTime.map_time_to_steps(hours=1200),
                     warm_up=DateTime.map_time_to_steps(hours=200), num_replications=25, multiprocessing=True)


if __name__ == '__main__':
    main()
