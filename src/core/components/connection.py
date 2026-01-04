import logging
from collections import deque

from simpy import Environment

from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.components_abstract.resetable_named_object import ResetAbleNamedObject, ResetAbleNamedObjectManager
from src.core.components_abstract.routing_object import RoutingObject
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.types.componet_type import ComponentType


class Connection(ResetAbleNamedObject, RoutingObject):
    """
    Represents a connection between components in a discrete event simulation.
    """

    connections = ResetAbleNamedObjectManager()
    """Manages all existing connection instances."""

    def __init__(self, env: Environment, origin_component, next_component, name: str,
                 process_duration: float = None, probability: float = None, entity_type: str = None, vehicle=None):
        """
        Initialize a Connection instance.

        :param env: SimPy environment
        :param origin_component: The component from which entities originate
        :param next_component: The next component to which entities are routed
        :param name: Name of the connection
        :param process_duration: Optional duration for processing entities in the connection
        :param probability: Optional probability for routing to the next component
        :param entity_type: Optional entity type for the connection
        :param vehicle: Optional vehicle for transporting entities
        """

        super().__init__(env, name, ComponentType.CONNECTIONS, Connection.connections)
        RoutingObject.__init__(self, env)

        self.probability = probability
        self.entity_type = entity_type
        self.entities_processed = 0
        self.number_entered = 0
        self.entities_queue = deque()
        self.origin_component = origin_component
        self.next_component = next_component
        self.processing = env.event()
        self.process_duration = process_duration
        self.action = env.process(self.run())
        self.vehicle = vehicle

    def reset(self):
        """
        Reset the connection by clearing the entities processed and the entity queue.
        """
        self.entities_processed = 0
        self.entities_queue.clear()
        self.number_entered = 0

    def reinitialize_process(self, env: Environment):
        """
        Reinitialize the connection's process with a new environment.
        This is called after a reset when starting a new simulation.

        :param env: New SimPy environment
        """
        self.env = env
        self.processing = env.event()
        self.action = env.process(self.run())

    def handle_entity_arrival(self, entity: Entity):
        """
        Handle the arrival of an entity at the connection.

        :param entity: The entity arriving at the connection
        """
        self.entities_queue.append(entity)

        if not self.processing.triggered:
            self.processing.succeed()

    def run(self):
        """
        Run the connection process, handling entity processing and routing.
        """

        while True:
            if self.entities_queue:
                entity = self.entities_queue.popleft()
                self.number_entered += 1

                if self.process_duration:
                    yield self.env.timeout(self.process_duration)

                # self.processing = self.env.event()

                self.log_and_process(self.origin_component, self.next_component, entity)
                self.entities_processed += 1

                # yield self.processing
            else:
                self.processing = self.env.event()
                yield self.processing

    @staticmethod
    def log_and_process(component, next_component, entity: Entity):
        """
        Log the processing of an entity and route it to the next component.

        :param component: The current component
        :param next_component: The next component to which the entity is routed
        :param entity: The entity being processed
        """

        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join([component.name, " added ", entity.name, " to ", next_component.name]),
            DateTime.get(component.env.now)))

        next_component.handle_entity_arrival(entity)
        component.number_exited += 1

    def __repr__(self) -> str:
        """
        String representation of the connection instance.

        :return: Name of the connection
        """
        return self.name
