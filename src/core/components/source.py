import logging
import random
from typing import Union, Type, Callable, Optional, Tuple

import numpy
import pandas as pd

import src.core.statistics.entity_type_utils as et
from src.core.event.block_event import BlockEvent
from src.core.statistics.entity_type_utils import initialize_entity_types_source
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
import src.core.global_imports as gi
from src.core.components.entity import Entity
from src.core.utils.helper import get_value_from_distribution_with_parameters, validate_probabilities, \
    create_connection_cache, execute_trigger, validate_entity_weights
from src.core.components.date_time import DateTime
from src.core.components_abstract.resetable_named_object import ResetAbleNamedObject
from src.core.components_abstract.routing_object import RoutingObject
from src.core.components.model import Model, ComponentType


class Source(ResetAbleNamedObject, RoutingObject):
    """
    A source is a component that creates entities and routes them to the next component.
    """
    sources = Model().get_component(ComponentType.SOURCES)
    """
    A list of all the sources in the simulation.
    """

    def __init__(self, env,
                 name,
                 creation_time_distribution_with_parameters=None,
                 arrival_table_file=None,
                 routing_expression=None,
                 entity_type: str = "Default",
                 entity_class: Type[Entity] | list[Type[Entity]] | dict[Type[Entity]: float] = Entity,
                 entity_class_column_name: str = None,
                 is_parent_source: bool = None,
                 sequence_routing: bool = False,
                 inital_sequence_index: int = 0,
                 max_arrival: int = None,
                 arrival_table_config: dict = None,
                 position: Tuple[float, float, float] = None,
                 before_creation_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 after_creation_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 vehicle_group: str = None) -> None:
        """
        Create a source.

        :param env: SimPy environment
        :param name: Name of the source
        :param creation_time_distribution_with_parameters: Tuple of distribution function and parameters
        :param arrival_table_file: Arrival table file name (CSV format).
        :param routing_expression: Function defining the routing logic.
        :param entity_type: Type of entities to be created. # TODO Rewrite
        :param entity_class: Class of entities to be created.
        :param entity_class_column_name: Column name of entity class to be created.
        :param sequence_routing: Whether sequence routing is used for the outgoing connection.
        :param inital_sequence_index: The inital sequnece index for the entinties
        :param arrival_table_parameter_name: Dictionary defining the name of columns for the parameters of the entity.
        :param max_arrival: Maximum number of entities to create
        :param arrival_table_config: Configuration for reading the arrival table
        :param before_creation_trigger: Function or tuple to be called before entity creation
        :param after_creation_trigger: Function or tuple to be called after entity creation
        """

        self.entities = []

        super().__init__(env, name, ComponentType.SOURCES, Source.sources)
        RoutingObject.__init__(self, env, routing_expression, sequence_routing)

        self.name = name
        self.creation_time_dwp = creation_time_distribution_with_parameters
        self.entity_class = entity_class
        self.entity_class_column_name = entity_class_column_name
        self.entity_type = entity_type

        # Add-on process triggers
        self.before_creation_trigger = before_creation_trigger
        self.after_creation_trigger = after_creation_trigger

        if arrival_table_file:
            if arrival_table_config:
                self.arrival_table = pd.read_csv(arrival_table_file, sep=arrival_table_config['sep'],
                                                 decimal=arrival_table_config['decimal'])
            else:
                self.arrival_table = pd.read_csv(arrival_table_file)
            self.arrival_table_index = 0
            self.arrival_table_column_name = list(self.arrival_table.columns)[0]
        else:
            self.arrival_table = None
            self.arrival_table_index = None

        self.action = env.process(self.run())

        self.is_parent_source = is_parent_source  # Defines if this source produces parents
        self.inital_sequnece_index = inital_sequence_index
        self.max_arrival = max_arrival

        self.entity_type_stats_source = {}

        # Vehicle management and coordinates
        self.position = position
        self.vehicle_group = vehicle_group

        # Capacity management
        self.capa_id = 0
        self.block_event = {0: None}

        if type(self.entity_class) is list:
            self.entity_name_dict = {c.__name__: c for c in self.entity_class}

        if type(self.entity_class) is dict:
            validate_entity_weights(self.name, self.entity_class)

    def reset(self):
        """
        Reset the source state. Clears the list of entities and resets counters.
        """
        self.next_components = []
        self.entities_created_pivot_table = 0
        self.entities = []
        self.number_exited_pivot_table = 0
        self.entity_type_stats_source = {}

    def run(self):
        """
       Run the source. Create entities and route them to the next component.
       This function is executed as a SimPy process.
       """
        validate_probabilities(self)
        create_connection_cache(self)

        while True:
            if self.arrival_table is not None:
                if self.arrival_table.shape[0] == self.arrival_table_index:
                    yield self.env.event()

            wait_time = self.arrival_table_based_wait_time() if self.arrival_table is not None else (
                get_value_from_distribution_with_parameters(self.creation_time_dwp))

            self.generate_single_entity()

            if type(self.block_event[self.capa_id]) is BlockEvent:
                yield self.block_event[self.capa_id]
                self.block_event[self.capa_id] = None

            yield self.env.timeout(wait_time)

            if self.max_arrival is not None:
                if self.entities_created_pivot_table == self.max_arrival:
                    yield self.env.event()

    def arrival_table_based_wait_time(self) -> Union[int, float]:
        """
        Get the wait time from the arrival table and increment the index for the next wait time.

        :return: The time to wait before the next entity creation.
        """

        wait_time = self.arrival_table.at[self.arrival_table_index, self.arrival_table_column_name] - self.env.now

        self.arrival_table_index += 1

        # Simpy timeout can't handle numpy.int64
        return int(wait_time) if isinstance(wait_time, numpy.int64) else wait_time

    def generate_single_entity(self):
        """
        Generate a single entity and route it to the next component.
        """
        # Execute before_creation_trigger
        if not execute_trigger(self.before_creation_trigger, self, None):
            # If trigger returns False, skip entity creation
            return

        if self.arrival_table is None:
            if type(self.entity_class) is dict:
                entity_class = self._choose_entity_weighted()
                entity = None
                entity = entity_class(
                    f"{self.entity_type}_Entity_{self.entities_created_pivot_table}",
                    self.env.now,
                    self.entity_type,
                    is_parent=self.is_parent_source,
                    sequence_index=self.inital_sequnece_index
                )

            if type(self.entity_class) is not list and type(self.entity_class) is not dict:
                entity = self.entity_class(
                    f"{self.entity_type}_Entity_{self.entities_created_pivot_table}",
                    self.env.now,
                    self.entity_type,
                    is_parent=self.is_parent_source,
                    sequence_index=self.inital_sequnece_index
                )
        else:
            param = {}

            for column in self.arrival_table.columns:
                if column != self.arrival_table_column_name and column != self.entity_class_column_name:
                    param[column] = self.arrival_table.at[self.arrival_table_index - 1, column]

            if type(self.entity_class) is list:
                entity_class = self.entity_name_dict[self.arrival_table.at[self.arrival_table_index - 1, self.entity_class_column_name]]

                entity = entity_class(
                    f"{self.entity_type}_Entity_{self.entities_created_pivot_table}",
                    self.env.now,
                    **param
                )

            if type(self.entity_class) is not list and type(self.entity_class) is not dict:
                entity = self.entity_class(
                    f"{self.entity_type}_Entity_{self.entities_created_pivot_table}",
                    self.env.now,
                    **param
                )

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[SourceStats] Source={self.name}, Status=busy, Entity={entity.name} , Created={self.entities_created_pivot_table}", DateTime.get(self.env.now))
        )

        if gi.COLLECT_ENTITY_TYPE_STATS:
            initialize_entity_types_source(entity_type_stats=self.entity_type_stats_source, entity=entity)

        if self.env.now >= gi.DURATION_WARM_UP:
            self.entities_created_pivot_table += 1
            self.number_exited_pivot_table += 1

        if gi.COLLECT_ENTITY_TYPE_STATS:
            # Werte für den spezifischen Entity-Typ erhöhen
            self.entity_type_stats_source[entity.entity_type][et.NUMBER_CREATED] += 1
            self.entity_type_stats_source[entity.entity_type][et.NUMBER_EXITED] += 1

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[Source] {self.name} created {entity.name} ", DateTime.get(self.env.now))
        )

        # Execute after_creation_trigger
        if not execute_trigger(self.after_creation_trigger, self, entity):
            # If trigger returns False, skip routing the entity
            return

        # Add to entities list and route to the next component
        self.entities.append(entity)
        self.route_entity(entity, self.vehicle_group, self.capa_id)

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[SourceStats] {self.name}, Status=idle, Entity=- , Exited={self.number_exited_pivot_table} ", DateTime.get(self.env.now))
        )

    def __repr__(self) -> str:
        """
        String representation of the source instance name

        :return: name
        """
        return self.name

    def _choose_entity_weighted(self):

        classes = list(self.entity_class.keys())
        weights = list(self.entity_class.values())

        return random.choices(classes, weights=weights, k=1)[0]
