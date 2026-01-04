from src.core.simulation.simulation import run_simulation
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.global_imports import random


def setup_model(env):
    source = Source(env, "Source1", (random.expovariate, 1 / 1.25))
    server = Server(env, "Server1", (lambda: 1,))
    sink = Sink(env, "Sink1")

    source.connect(server)
    server.connect(sink)


def main():
    print("\n" + "=" * 80)
    print("Without Warm Up")
    print("=" * 80, "\n")
    run_simulation(model=setup_model, steps=1000)
    print("\n" + "=" * 80)
    print("With Warm Up")
    print("=" * 80, "\n")
    run_simulation(model=setup_model, steps=1000, warm_up=200)


if __name__ == '__main__':
    main()
