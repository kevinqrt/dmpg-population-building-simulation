from src.core.global_imports import random
from src.core.components.entity import Entity
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_simulation, run_replications
from typing import Union


class SubEntity(Entity):
    """
    Represents a sub-entity that extends the generic Entity class with additional attributes.
    """

    def __init__(self, name: str,
                 creation_time: Union[int, float],
                 entity_type: str = "Default",
                 is_parent: bool = None,
                 sequence_index=None) -> None:
        """
        Initialize a SubEntity instance.

        :param name: The name of the sub-entity.
        :param creation_time: The creation time of the sub-entity.
        :param entity_type: The type of the sub-entity.
        """

        super().__init__(name, creation_time, entity_type)
        self.num_times_processed = 0
        self.server_history = []

        if sequence_index is not None:
            self.sequence_index = sequence_index

    def count_processing(self) -> None:
        """
        Increment the count of times this sub-entity has been processed.
        """
        self.num_times_processed += 1

    def add_to_server_history(self, server: str) -> None:
        """
        Add a server to the processing history of this sub-entity.

        :param server: The name of the server to add to the history.
        """
        self.server_history.append(server)

    def __repr__(self):
        """
        Provide a string representation of the SubEntity instance, showing its lifecycle.

        :return: A string representation of the sub-entity, including its name, creation time,
        and destruction time (if any).
        """

        return f"{self.name} ({self.creation_time})" if not self.destruction_time \
            else f"{self.name} ({self.destruction_time - self.creation_time})"


# Define trigger functions
def after_processing_trigger(server, entity, *args, **kwargs):
    """
    Trigger function to update entity processing count and server history.
    """
    # Only process SubEntity objects
    if isinstance(entity, SubEntity):
        entity.count_processing()
        entity.add_to_server_history(server.name)
        print(f"[{server.env.now:.2f}] {server.name}: Entity {entity.name} processed, count: {entity.num_times_processed}")
    return True


def before_routing_trigger(server, entity, *args, **kwargs):
    """
    Trigger function that checks processing count before routing.
    If the entity has been processed too many times, override normal routing.
    """
    # Check if we're in the inspection server
    if server.name == "Inspection" and isinstance(entity, SubEntity):
        max_processing_count = 11

        print(f"[{server.env.now:.2f}] {server.name}: Checking routing for {entity.name} - processed: {entity.num_times_processed}/{max_processing_count}")

        if entity.num_times_processed >= max_processing_count:
            print(f"[{server.env.now:.2f}] {server.name}: ⚠️ Entity {entity.name} exceeded max processing limit! Forcing to BadParts.")
            # Find the BadParts sink in connections
            for cumulative_probability, (connection, vehicle) in server.connection_cache.items():
                if connection.next_component.name == "BadParts":
                    # Override normal routing by routing directly to BadParts
                    print(f"[{server.env.now:.2f}] {server.name}: Forcing entity {entity.name} to {connection.next_component.name}")
                    connection.next_component.handle_entity_arrival(entity)
                    server.number_exited_pivot_table += 1
                    # Return False to prevent normal routing
                    return False

    # Return True to use normal probability-based routing
    return True


def after_entity_destruction(sink, entity, *args, **kwargs):
    """
    Trigger function to record processing count after entity destruction.
    """
    if isinstance(entity, SubEntity):
        sink.tally_statistic.record(entity.num_times_processed)
        print(f"[{sink.env.now:.2f}] {sink.name}: Entity {entity.name} destroyed. Total processes: {entity.num_times_processed}")
        print(f"[{sink.env.now:.2f}] {sink.name}: Processing history: {' -> '.join(entity.server_history)}")
    return True


def combined_inspection_trigger(server, entity, *args, **kwargs):
    """
    Combined trigger for inspection server that both counts processing and checks limits.
    """
    # First run the standard processing update
    after_processing_trigger(server, entity, *args, **kwargs)

    # For entities over the limit, route to BadParts
    if isinstance(entity, SubEntity) and entity.num_times_processed >= 11:
        print(f"[{server.env.now:.2f}] {server.name}: ⚠️ Entity {entity.name} exceeded max processing limit! Forcing to BadParts.")
        # Find the BadParts sink and route there
        for cumulative_probability, (connection, vehicle) in server.connection_cache.items():
            if connection.next_component.name == "BadParts":
                print(f"[{server.env.now:.2f}] {server.name}: Forcing entity {entity.name} to {connection.next_component.name}")
                connection.next_component.handle_entity_arrival(entity)
                server.number_exited_pivot_table += 1
                return False
    return True


def setup_model_pcb(env):

    # Create servers, sinks, and sources
    source1 = Source(env, "PCB", (random.expovariate, 1 / 6),
                     entity_class=SubEntity,
                     after_creation_trigger=lambda
                     source, entity: print(f"[{source.env.now:.2f}] Created entity: {entity.name}") or True)

    # Add debug prints to track entity flow
    def debug_before_arrival(server, entity, *args, **kwargs):
        print(f"[{server.env.now:.2f}] {server.name}: Entity {entity.name} arrived")
        return True

    # Server with after_processing_trigger to count processing and update history
    server1 = Server(env, "Placement", (random.triangular, 3, 5, 4),
                     before_arrival_trigger=debug_before_arrival,
                     after_processing_trigger=after_processing_trigger)
    server2 = Server(env, "FinePitchFast", (random.triangular, 8, 10, 9),
                     before_arrival_trigger=debug_before_arrival,
                     after_processing_trigger=after_processing_trigger)
    server3 = Server(env, "FinePitchMedium", (random.triangular, 18, 22, 20),
                     before_arrival_trigger=debug_before_arrival,
                     after_processing_trigger=after_processing_trigger)
    server4 = Server(env, "FinePitchSlow", (random.triangular, 22, 26, 24),
                     before_arrival_trigger=debug_before_arrival,
                     after_processing_trigger=after_processing_trigger)
    server5 = Server(env, "Inspection", (random.uniform, 2, 4),
                     before_arrival_trigger=debug_before_arrival,
                     after_processing_trigger=combined_inspection_trigger)
    server6 = Server(env, "Rework", (random.triangular, 2, 6, 4),
                     before_arrival_trigger=debug_before_arrival,
                     after_processing_trigger=after_processing_trigger)

    # Sinks with after_destruction_trigger to record processing count
    sink1 = Sink(env, "GoodParts", after_processing_trigger=after_entity_destruction)
    sink2 = Sink(env, "BadParts", before_processing_trigger=after_entity_destruction)

    # Set up connections with routing probabilities for servers
    source1.connect(server1)

    server1.connect(server2)
    server1.connect(server3)
    server1.connect(server4)
    server2.connect(server5)
    server3.connect(server5)
    server4.connect(server5)
    server6.connect(server1)

    server5.connect(sink1, 66)      # 66% probability to route to GoodParts
    server5.connect(sink2, 8)       # 8% probability to route to BadParts
    server5.connect(server6, 26)    # 26% probability to route to Rework


def main():
    run_simulation(model=setup_model_pcb, steps=400)
    run_replications(model=setup_model_pcb, steps=1800, num_replications=100, multiprocessing=True)


if __name__ == '__main__':
    main()
