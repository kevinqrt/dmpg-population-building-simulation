from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_simulation, run_replications
from src.core.components.date_time import DateTime


def setup_model4_1(env):
    source1 = Source(env, "Source1", (random.expovariate, 1 / 1.25))
    server1 = Server(env, "Server1", (random.expovariate, 1))
    sink1 = Sink(env, "Sink1")

    source1.connect(server1)
    server1.connect(sink1)


def main():
    run_simulation(model=setup_model4_1, steps=DateTime.map_time_to_steps(days=1))          # 1 day
    # print(pivot_table.at[('Entity', 'Entity', 'AvgTimeInSystem'), 'Value'])               # 6.0036

    # m1-max 10 cores
    # intel i9-10980XE@3GHz 18 cores

    # v0.1      0:03 iteration & 0:33 total       (m1)
    # v0.4      0:14 iteration & 2:20 total       (m1)

    # v0.4.1    0:17 iteration & 2:54 total       (m1)
    # v0.4.1    0:39 iteration & 6:18 total       (intel)

    # v0.4.3    0:13 iteration & 2:19 total       (m1)
    # v0.4.3    0:29 iteration & 4:56 total       (intel)

    # v0.4.4    0:12 iteration & 2:06 total       (m1)
    # v0.4.4    0:27 iteration & 4:35 total       (intel)
    run_replications(model=setup_model4_1, steps=DateTime.map_time_to_steps(days=7), num_replications=100, multiprocessing=False, warm_up=DateTime.map_time_to_steps(minutes=15))

    # v0.1      0:25 iteration & 4:00 total       (m1)
    # v0.4      1:45 iteration & 4:00 total       (m1)

    # v0.4.1    2:00 iteration & 20:00 total      (m1)
    # v0.4.1    2:00 iteration & 20:00 total      (intel)

    # v0.4.3    1:32 iteration & 15:22 total      (m1)
    # v0.4.3    1:38 iteration & 16:22 total      (intel)

    # v0.4.4    1:24 iteration & 14:03 total      (m1)
    # v0.4.4    1:30 iteration & 15:06 total      (intel)
    run_replications(model=setup_model4_1, steps=DateTime.map_time_to_steps(days=365), num_replications=1000, multiprocessing=True)


if __name__ == '__main__':
    main()
