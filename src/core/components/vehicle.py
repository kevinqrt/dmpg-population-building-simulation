import logging
from typing import Callable, Tuple, List

import numpy as np
import simpy

import src.core.global_imports as gi
import src.core.statistics.entity_type_utils as et
from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.components.model import Model, ComponentType
from src.core.components.vehicle_manager import VehicleManager
from src.core.components_abstract.resetable_named_object import ResetAbleNamedObject
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.statistics.entity_type_utils import initialize_entity_types_vehicle
from src.core.utils.helper import get_value_from_distribution_with_parameters


class Vehicle(ResetAbleNamedObject):
    """
    Represents a vehicle that transports entities between components.
    The capacity represents the number of entities the vehicle can transport simultaneously.
    The resource capacity defines how many concurrent trips the vehicle can handle.
    """
    vehicles = Model().get_component(ComponentType.VEHICLES)
    """Manages all existing vehicle instances."""

    def __init__(self, env: simpy.Environment, name: str, travel_time_dwp: Tuple[Callable, ...] = None,
                 vehicle_capacity: int = 1, vehicle_group: str = 'DefaultVehicleGroup', resource_capacity: int = 1, batching: bool = False, transport_queue: str = None,
                 travel_time_expression: Tuple[Callable, ...] = None,):
        """
        Initialize a Vehicle instance.

        :param env: SimPy environment
        :param name: Name of the vehicle
        :param travel_time_dwp: A tuple specifying the distribution and its parameters for travel time
        :param vehicle_capacity: The maximum number of entities the vehicle can transport simultaneously
        :param vehicle_group: The group in which the vehicle can be found
        :param resource_capacity: The number of concurrent trips the vehicle can handle
        :param batching: Whether to enable batching (accumulate entities until vehicle capacity is reached).
        """
        super().__init__(env, name, ComponentType.VEHICLES, Vehicle.vehicles)

        self.env = env
        self.name = name
        self.travel_time_dwp = travel_time_dwp
        self.travel_time_expression = travel_time_expression
        self.vehicle_capacity = vehicle_capacity  # Max number of entities it can carry at once
        self.batching = batching
        self.entity_queue: List[Tuple[Entity, Callable, float]] = []
        self.idle: bool = True
        # resource_capacity controls trips can run concurrently.
        self.resource = simpy.Resource(env, capacity=resource_capacity)

        self.time_idle_start = self.env.now

        self.entity_types_vehicle = {}

        # Vehicle manager
        self.transport_queue = transport_queue
        self.position = None
        self.current_location = None
        self.home_point = None

        # Collusion managment
        self.lower_bound = None
        self.upper_bound = None

        # Vehicle Management
        VehicleManager().add_vehicle_to_group(vehicle_group, self)

    def handle_entity_arrival(self, entity: Entity, destination):
        """
        Handle the arrival of an entity for transportation.

        :param entity: The entity to transport
        :param destination: The destination component
        """
        if gi.COLLECT_ENTITY_TYPE_STATS:
            initialize_entity_types_vehicle(entity_type_stats=self.entity_types_vehicle, entity=entity)

        queue_entry_time = self.env.now
        self.entity_queue.append((entity, destination, queue_entry_time))

        # Track queue length
        self.current_queue_length += 1
        self.queue_lengths.append(self.current_queue_length)

        if gi.COLLECT_ENTITY_TYPE_STATS:
            stats = self.entity_types_vehicle[entity.entity_type]
            stats[et.QUEUE_LENGTH] += 1
            stats[et.TOTAL_ENTITES_IN_QUEUE] += 1
            stats[et.QUEUE_LENGTHS].append(stats[et.QUEUE_LENGTH])
            stats[et.MAX_ENTITES_IN_QUEUE] = max(stats[et.MAX_ENTITES_IN_QUEUE], stats[et.QUEUE_LENGTH])

        # Check if the vehicle can start transporting: only transport when batching is met or no batching
        if len(self.entity_queue) >= self.vehicle_capacity or not self.batching:
            # Request the vehicle resource before initiating transport
            # if len(self.resource.users) < self.resource.capacity:  # Check if vehicle can take another trip
            self.env.process(self.start_transport())

    def start_transport(self):
        """
        Handles the vehicle transport process by requesting the vehicle resource.
        This ensures that only one trip happens at a time, or more if resource capacity allows it.
        """
        with self.resource.request() as request:
            yield request  # Wait for the vehicle resource to become available

            # Begin transport process now that the resource is allocated
            yield self.env.process(self.transport_entities())

    def transport_entities(self):
        """
        Transport entities from the queue based on the batching setting.
        """
        # Handle batching: Transport multiple entities if batching, otherwise transport whatever is available
        if self.batching:
            entities_to_transport = self.entity_queue[:self.vehicle_capacity]
            self.entity_queue = self.entity_queue[self.vehicle_capacity:]
        else:
            entities_to_transport = self.entity_queue[:min(len(self.entity_queue), self.vehicle_capacity)]
            self.entity_queue = self.entity_queue[len(entities_to_transport):]

        # Calculate queue times for the entities being transported
        for entity, destination, queue_entry_time in entities_to_transport:
            self.current_queue_length -= 1
            queue_exit_time = self.env.now
            queue_time = queue_exit_time - queue_entry_time
            self.queue_times.append(queue_time)

        self.idle = False

        if self.travel_time_dwp:
            travel_time = get_value_from_distribution_with_parameters(self.travel_time_dwp)
        if self.travel_time_expression:
            travel_time = self.travel_time_expression(self, entity)
            if gi.COLLECT_ENTITY_TYPE_STATS:
                # EntityType-spezifische QueueStats aktualisieren
                if entity.entity_type in self.entity_types_vehicle:
                    stats = self.entity_types_vehicle[entity.entity_type]
                    stats[et.QUEUE_LENGTH] -= 1
                    stats[et.QUEUE_TIMES].append(queue_time)
                    stats[et.MAX_TIME_IN_QUEUE] = max(stats[et.MAX_TIME_IN_QUEUE], queue_time)

        travel_time = get_value_from_distribution_with_parameters(self.travel_time_dwp)

        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join([self.name, " transporting ", str(len(entities_to_transport)), " entities. Travel time: ",
                     str(travel_time)]), DateTime.get(self.env.now)))

        # Track utilization
        idle_time = 0
        if self.time_idle_start is not None:
            idle_time = self.env.now - self.time_idle_start

        if self.env.now >= gi.DURATION_WARM_UP:
            self.utilized_time -= idle_time

        # Mark vehicle as in use
        self.time_idle_start = None

        # Simulate transport time
        yield self.env.timeout(travel_time)

        # Handle entity arrivals at the destination
        for entity, destination, _ in entities_to_transport:
            self.current_location = destination
            destination.handle_entity_arrival(entity)
            self.entities_transported += 1

            if gi.COLLECT_ENTITY_TYPE_STATS:
                stats = self.entity_types_vehicle[entity.entity_type]
                stats["EntitiesTransported"] += 1

        # Track travel time and mark the vehicle idle after transport
        self.total_travel_time += travel_time
        if self.env.now >= gi.DURATION_WARM_UP:
            self.time_utilized_over_time.append((self.env.now - travel_time, self.env.now, len(entities_to_transport)))
        self.time_idle_start = self.env.now

        # Log statistics
        self.total_trips += 1

        # set new state
        if destination.position is not None:
            self.upper_bound = destination.position[1]
            self.lower_bound = destination.position[1]
        self.idle = True

        if self.transport_queue:
            VehicleManager().request_entity(self.transport_queue, self)

    def move_to_location(self, destination):
        travel_time = get_value_from_distribution_with_parameters(self.travel_time_dwp)
        yield self.env.timeout(travel_time)

        # Track utilization
        idle_time = 0
        if self.time_idle_start is not None:
            idle_time = self.env.now - self.time_idle_start

        if self.env.now >= gi.DURATION_WARM_UP:
            self.utilized_time -= idle_time

    def return_to_home(self):
        self.lower_bound = min([self.home_point.position[1], self.current_location.position[1]])
        self.upper_bound = max([self.home_point.position[1], self.current_location.position[1]])
        travel_time = get_value_from_distribution_with_parameters(self.travel_time_dwp)
        self.current_location = self.home_point
        self.position = self.home_point.position
        self.upper_bound = self.position[1]
        self.lower_bound = self.position[1]
        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join([self.name, " transporting ", self.current_location.name, " to ", self.home_point.name, ". Travel time: ",
                     str(travel_time)]), DateTime.get(self.env.now)))

        yield self.env.timeout(travel_time)

    def set_home_point(self, home_point):
        self.position = home_point.position
        self.home_point = home_point
        self.current_location = home_point

    def reset(self):
        """Reset the vehicle's state."""
        self.total_trips = 0
        self.total_travel_time = 0
        self.entities_transported = 0
        self.time_idle_start = self.env.now
        self.utilized_time = 0
        self.time_utilized_over_time = []
        self.queue_lengths = []
        self.queue_times = []
        self.current_queue_length = 0

    def __repr__(self) -> str:
        """Return the name of the vehicle when called by the print function."""
        return self.name

    def finalize_statistics_per_entity_type(self, sim_time):
        """
        Calculate final average values for per-entity-type queue stats.
        """
        for entity_type, stats in self.entity_types_vehicle.items():
            if stats[et.QUEUE_LENGTHS]:
                stats[et.AVG_ENTITES_IN_QUEUE] = np.mean(stats[et.QUEUE_LENGTHS])
            if stats[et.QUEUE_TIMES]:
                stats[et.AVG_TIME_IN_QUEUE] = np.mean(stats[et.QUEUE_TIMES])
            if stats["TravelTime (total)"]:
                stats["TravelTime (average)"] = stats["TravelTime (total)"] / stats["TotalTrips"]
