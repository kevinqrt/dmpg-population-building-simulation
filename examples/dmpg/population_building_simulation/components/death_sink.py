"""
DeathSink handles the destruction of humans who die in the simulation.
"""
import simpy

from examples.dmpg.population_building_simulation.components.human_entity import Human
from src.core.components.model import Model
from src.core.components.sink import Sink


class DeathSink(Sink):
    """
    A Sink component that handles human deaths.

    When a human is sent to this sink, they are:
    1. Removed from the humans list
    2. Removed from their home
    3. Destroyed by the Sink
    """

    def __init__(self, env: simpy.Environment, name: str = "DeathSink"):
        super().__init__(
            env=env,
            name=name,
            processing_time_distribution_with_parameters=None,  # Instant death
            capacity=1000,  # High capacity to handle multiple deaths
        )
        self.total_deaths = 0

    def handle_entity_arrival(self, entity: Human) -> None:
        """
        Handle a human arriving at the death sink.
        Removes them from the population before standard sink processing.
        """

        # Remove from humans list
        humans_list = Model().get_state("humans")
        if entity in humans_list:
            humans_list.remove(entity)

        # Remove from their home
        if entity.home_name:
            home = Model().get_component_by_name(entity.home_name)
            if home and hasattr(home, "handle_entity_departure"):
                home.handle_entity_departure(entity)

        # Mark as dead
        entity.is_dead = True
        self.total_deaths += 1

        # Update population count
        pop = Model().get_state("population")
        Model().update_state("population", pop - 1)

        # Let the Sink handle destruction
        super().handle_entity_arrival(entity)
