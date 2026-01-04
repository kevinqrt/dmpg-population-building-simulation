from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.entity import Entity
from src.core.simulation.simulation import run_simulation
from enum import Enum


class ProductStatus(Enum):
    GOOD = "GOOD"
    DEFECTIVE = "DEFECTIVE"


class ProductEntity(Entity):
    def __init__(self, name, creation_time, entity_type="Product", **kwargs):
        super().__init__(name, creation_time, entity_type, **kwargs)
        self.defect_probability = 0
        self.status = ProductStatus.GOOD
        self.processing_history = []


# Define trigger functions
def before_entity_creation(source, entity):
    print(f"[{source.env.now:.2f}] {source.name}: About to create a new entity")
    return True  # Proceed with creation


def after_entity_creation(source, entity):
    # 50% chance to mark entity as defective at creation
    entity.defect_probability = random.random() * 0.50
    print(f"[{source.env.now:.2f}] {source.name}: Created {entity.name} with defect probability {entity.defect_probability:.2f}")
    return True  # Proceed with routing


def before_server_arrival(server, entity):
    print(f"[{server.env.now:.2f}] {server.name}: Entity {entity.name} arriving")
    return True  # Accept the entity


def after_server_arrival(server, entity):
    print(f"[{server.env.now:.2f}] {server.name}: Entity {entity.name} queued for processing")
    # Add optional logic here
    return True


def before_server_processing(server, entity, worker=None):
    # Increase defect probability by 1% in Manufacturing
    if server.name == "Manufacturing":
        entity.defect_probability += 0.1

    # Log worker assignment if applicable
    worker_info = ""
    if isinstance(worker, list) and worker:
        worker_info = f" with {len(worker)} workers"
    elif worker is not None:
        worker_info = f" with worker {worker.id}"

    print(f"[{server.env.now:.2f}] {server.name}: Starting to process {entity.name}{worker_info}")
    return True  # Proceed with processing


def after_server_processing(server, entity, worker=None, processing_time=None):
    # Add server to entity's history
    entity.processing_history.append(server.name)

    # In QualityControl, determine if entity is defective
    if server.name == "QualityControl":
        entity.status = ProductStatus.DEFECTIVE if random.random() < entity.defect_probability else ProductStatus.GOOD
        print(f"[{server.env.now:.2f}] {server.name}: {entity.name} inspected - {entity.status.value}")
    else:
        print(f"[{server.env.now:.2f}] {server.name}: Completed processing {entity.name} in {processing_time:.2f} units")

    return True  # Proceed with routing


def before_entity_destruction(sink, entity):
    # Log entity statistics before destruction
    time_in_system = sink.env.now - entity.creation_time
    if not hasattr(entity, "status"):
        entity.status = ProductStatus.GOOD
    history = " -> ".join(getattr(entity, "processing_history", ["Unknown"]))

    print(f"[{sink.env.now:.2f}] {sink.name}: About to destroy {entity.name}")
    print(f"  - Status: {entity.status.value}")
    print(f"  - Time in system: {time_in_system:.2f}")
    print(f"  - Processing history: {history}")

    return True  # Proceed with destruction


def after_entity_destruction(sink, entity):
    print(f"[{sink.env.now:.2f}] {sink.name}: Entity {entity.name} has been destroyed")
    return True


def setup_trigger_example(env):
    # Create components with triggers
    source = Source(
        env, "ProductionLine",
        (random.expovariate, 1 / 5),
        entity_class=ProductEntity,
        before_creation_trigger=before_entity_creation,
        after_creation_trigger=after_entity_creation
    )

    manufacturing = Server(
        env, "Manufacturing",
        (random.triangular, 3, 7, 5),
        before_arrival_trigger=before_server_arrival,
        after_arrival_trigger=after_server_arrival,
        before_processing_trigger=before_server_processing,
        after_processing_trigger=after_server_processing
    )

    quality_control = Server(
        env, "QualityControl",
        (random.uniform, 1, 3),
        before_arrival_trigger=before_server_arrival,
        after_arrival_trigger=after_server_arrival,
        before_processing_trigger=before_server_processing,
        after_processing_trigger=after_server_processing
    )

    good_products = Sink(
        env, "GoodProducts",
        before_processing_trigger=before_entity_destruction,
        after_processing_trigger=after_entity_destruction
    )

    defective_products = Sink(
        env, "DefectiveProducts",
        before_processing_trigger=before_entity_destruction,
        after_processing_trigger=after_entity_destruction
    )

    # Connect components
    source.connect(manufacturing)
    manufacturing.connect(quality_control)

    # Custom routing function for quality_control to route based on defect status
    def route_by_quality(server, entity):
        if entity.status == ProductStatus.DEFECTIVE:
            defective_products.handle_entity_arrival(entity)
        else:
            good_products.handle_entity_arrival(entity)

    # Set custom routing expression for quality_control
    quality_control.routing_expression = (route_by_quality,)


def main():
    print("Starting simulation with add-on process triggers")
    run_simulation(model=setup_trigger_example, steps=100)
    print("Simulation completed.")


if __name__ == '__main__':
    main()
