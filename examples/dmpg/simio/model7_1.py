from typing import Callable

from src.core.components.entity import EntityManager
from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_simulation


ROUTINE = "Routine"
MODERATE = "Moderate"
SEVERE = "Severe"
URGENT = "Urgent"

SERVER_1 = "Server1"

SINK_FINAL = "FinalSink"

POOL_SIZE_ROUTINE = 300
POOL_SIZE_MODERATE = 200
POOL_SIZE_SEVERE = 150
POOL_SIZE_URGENT = 100


def probabilistic_expovariate(probability: float, dwp: tuple[Callable[..., float]]):

    distribution, parameters = dwp[0], dwp[1:]
    time = 0

    r = random.random()
    while r > probability:
        time += distribution(*parameters)
        r = random.random()

    return time + distribution(*parameters)


def model7_1(env):

    EntityManager.max_pool_size_by_type[ROUTINE] = POOL_SIZE_ROUTINE
    EntityManager.max_pool_size_by_type[MODERATE] = POOL_SIZE_MODERATE
    EntityManager.max_pool_size_by_type[SEVERE] = POOL_SIZE_SEVERE
    EntityManager.max_pool_size_by_type[URGENT] = POOL_SIZE_URGENT

    patient_routine = Source(env, ROUTINE, (probabilistic_expovariate, 0.4, (random.expovariate, 1 / 4)), entity_type=ROUTINE)
    patient_moderate = Source(env, MODERATE, (probabilistic_expovariate, 0.31, (random.expovariate, 1 / 4)), entity_type=MODERATE)
    patient_severe = Source(env, SEVERE, (probabilistic_expovariate, 0.24, (random.expovariate, 1 / 4)), entity_type=SEVERE)
    patient_urgent = Source(env, URGENT, (probabilistic_expovariate, 0.05, (random.expovariate, 1 / 4)), entity_type=URGENT)

    processing_times = {
        SERVER_1: {
            ROUTINE: (random.triangular, 3, 10, 5),
            MODERATE: (random.triangular, 4, 15, 8),
            SEVERE: (random.triangular, 4, 15, 8),
            URGENT: (random.triangular, 15, 40, 25),
        }
    }

    server1 = Server(env, SERVER_1, global_processing_times=processing_times, capacity=2)
    final_sink = Sink(env, SINK_FINAL)

    patient_routine.connect(server1)
    patient_moderate.connect(server1)
    patient_severe.connect(server1)
    patient_urgent.connect(server1)

    server1.connect(final_sink)


def main():
    run_simulation(model=model7_1, steps=100)


if __name__ == '__main__':
    main()
