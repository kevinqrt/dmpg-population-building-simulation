from src.core.visualization.plots import plot_histogram, plot_box_plot
from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_replications
from src.core.components.date_time import DateTime
from src.core.global_imports import Stats


def setup_model4_3(env):

    source1 = Source(env, "Entrance", (random.expovariate, 1 / 1.25))
    server1 = Server(env, "ATM", (random.triangular, 0.25, 1.75, 1))
    sink1 = Sink(env, "Exit")

    source1.connect(server1, process_duration=DateTime.map_time_to_steps(seconds=10))
    server1.connect(sink1, process_duration=DateTime.map_time_to_steps(seconds=9.899))


def main():

    run_replications(model=setup_model4_3, steps=DateTime.map_time_to_steps(days=7), num_replications=10, multiprocessing=False, confidence=.9999)

    plot_box_plot(Stats, 'Server', 'ATM', 'ScheduledUtilization')
    plot_histogram(Stats, 'Sink', 'Exit', 'TimeInSystem (average)')


if __name__ == '__main__':
    main()
