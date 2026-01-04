from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_simulation


def server_ressource_test(env):

    # Define the source
    source = Source(env, "SourceEntities", (random.uniform, 0.101, 0.101), entity_type="TestMaterial")

    # Define processing times for the entity types
    processing_times = {
        "Server1": {
            "TestMaterial": (random.uniform, 1, 1)
        }
    }

    # Define the server
    server1 = Server(env, "Server1", global_processing_times=processing_times,
                     capacity=2)

    # Define the sink
    final_sink = Sink(env, "FinalSink")

    # Connect the components
    source.connect(server1)
    server1.connect(final_sink)


def main():
    # Run the simulation for 10 minutes
    run_simulation(model=server_ressource_test, steps=10.1)


if __name__ == '__main__':
    main()
