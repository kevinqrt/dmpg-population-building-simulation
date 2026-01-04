from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.vehicle import Vehicle
from src.core.simulation.simulation import run_simulation


def vehicle_test(env):
    # Define the sources
    source_wood = Source(env, "SourceWood", (random.expovariate, 1), entity_type="WoodMaterial")
    source_metal = Source(env, "SourceMetal", (random.expovariate, 1), entity_type="MetalMaterial")

    # Define processing times for different entity types
    processing_times = {
        "Workbench1": {
            "WoodMaterial": (random.uniform, 20, 40),
            "MetalMaterial": (random.uniform, 80, 100)
        },
        "Workbench2": {
            "WoodMaterial": (random.uniform, 1, 2),
            "MetalMaterial": (random.uniform, 12, 14)
        }
    }

    # Define the servers
    workbench1 = Server(env, "Workbench1", entity_processing_times={
        "WoodMaterial": (random.uniform, 2, 4),
        "MetalMaterial": (random.uniform, 4, 6)
    })
    workbench2 = Server(env, "Workbench2",
                        (random.uniform, 20, 40),
                        global_processing_times=processing_times)

    # Define the sink
    good_parts = Sink(env, "Goodparts")

    # Define the vehicle
    transport_vehicle = Vehicle(env, "TransportKran", (random.uniform, 2, 4))

    # Connect the components
    source_wood.connect(workbench1, vehicle=transport_vehicle)
    source_metal.connect(workbench1, vehicle=transport_vehicle)

    workbench1.connect(workbench2, entity_type="WoodMaterial")
    workbench2.connect(good_parts)


def main():
    run_simulation(model=vehicle_test, steps=20)


if __name__ == '__main__':
    main()
