from datetime import datetime
from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_simulation
from src.core.components.work_schedule import load_work_schedule_from_csv
from src.core.components.date_time import DateTime
from src.core.components.model import Model
from src.core.components.worker_pool import WorkerPool, load_workers_from_csv


def setup_work_schedule(env):
    # Set the simulation start datetime
    DateTime.set(datetime(2024, 4, 1, 2, 0, 0))

    # Load work schedule and workers from CSV
    week = load_work_schedule_from_csv("work_schedule.csv")
    workers = load_workers_from_csv("workers.csv")

    week.print_stats("week")

    # Create the worker pool using the loaded work schedule and workers
    Model().worker_pools = {
        "workers": WorkerPool(env, week, workers=workers)
    }

    # Build the simulation model
    source1 = Source(env, "Source1",
                     (random.expovariate, 1 / 1.25))

    server1 = Server(env, "Server1",
                     (random.expovariate, 1),
                     work_schedule=week,
                     worker_pool="workers")
    server2 = Server(env, "Server2",
                     (random.expovariate, 1),
                     work_schedule=week,
                     worker_pool="workers")
    server3 = Server(env, "Server3",
                     (random.expovariate, 1),
                     work_schedule=week,
                     worker_pool="workers")
    sink1 = Sink(env, "Sink1")

    source1.connect(server1)
    server1.connect(server2)
    server2.connect(server3)
    server3.connect(sink1)


def main():
    run_simulation(model=setup_work_schedule, steps=500)


if __name__ == '__main__':
    main()
