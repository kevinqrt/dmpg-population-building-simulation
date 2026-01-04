import logging

from simpy import Environment
from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.components.model import Model
from src.core.components.vehicle_manager import VehicleManager
from src.core.event.block_event import BlockEvent
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.global_imports import random
from src.core.utils.helper import execute_trigger


class RoutingObject:
    """
    Represents a routing object that handles the routing of entities between components.
    """

    def __init__(self, env: Environment, routing_expression=None, sequence_routing: bool = False, sequence_routing_trigger=None):
        """
        Initialize a RoutingObject instance.

        :param env: SimPy environment
        :param routing_expression: Optional routing expression to determine routing logic
        """
        self.sequence_routing_trigger = sequence_routing_trigger
        self.sequence_routing = sequence_routing
        self.env = env
        self.routing_expression = routing_expression
        self.next_components = []  # List of (component, probability, entity_type, vehicle)
        self.number_exited = 0
        self.connection_cache = {}
        self.connections = {}

    def route_entity(self, entity: Entity, vehicle_group: str = None, capa_id: int = None):
        """
        Route the entity to the next component based on the routing logic.

        :param entity: The entity to route
        """
        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join(["Routing entity ", entity.name, " of type ", entity.entity_type]), DateTime.get(self.env.now)))
        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join(["Connection cache before routing: ", str(self.connection_cache)]), DateTime.get(self.env.now)))

        # Priority 1: If there's a routing_expression, use it (for custom routing logic)
        if self.routing_expression:
            self._route_without_truck(entity, vehicle_group, capa_id)
            return

        # Priority 2: Check if the entity has a truck assigned for transport
        # Only use truck transport if the truck has the transport_to_next_component method
        truck = getattr(entity, "truck", None)
        if truck and hasattr(truck, 'transport_to_next_component'):
            # Use the truck to transport the entity to the next component
            self.env.process(self._transport_entity_with_truck(entity, truck))
        else:
            # Fallback to the default routing logic
            self._route_without_truck(entity, vehicle_group, capa_id)

    def _route_without_truck(self, entity: Entity, vehicle_group: str = None, capa_id=None, event: BlockEvent = None):
        """
        Apply default routing logic if no truck is assigned.

        :param entity: The entity to route
        """
        # Check that is only one enabled
        if self.sequence_routing and self.routing_expression:
            raise SystemExit('Error: Either sequence routing or routing expression!')

        # If sequence routing is enabled, use it
        if self.sequence_routing:
            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(f"Sequence routing {entity.name} with index {entity.sequence_index}",
                                                   DateTime.get(self.env.now)))

            if entity.destination is None:
                destination_name = Model().routing_table.at[entity.sequence_index, Model().routing_table_destination_column]
                if Model().is_group(destination_name):
                    entity.destination = Model().get_next_destination_from_group(destination_name)
                else:
                    entity.destination = Model().get_component_by_name(destination_name)

            destination = entity.destination
            event = event
            if destination is None:
                if event is None:
                    event = BlockEvent(self.env)
                    if capa_id is not None:
                        self.block_event[capa_id] = event
                    else:
                        self.block_event = event
                self.env.process(self.retry(10, self, entity, vehicle_group, capa_id, event))  # No destination free try again in WAITING_TIME (10 min / steps)
            else:
                destination_name = entity.destination.name

            if destination is not None:
                destination.used_capacity += 1
                entity.is_vehicle_routed = True
            # Execute after_processing_trigger
            if not execute_trigger(self.sequence_routing_trigger, self, entity, destination_name):
                # If trigger returns False, skip routing the entity
                # Handle any custom logic as needed
                pass
            else:
                # Route entity to next destination
                entity.sequence_index += 1
                entity.destination = None

            self.retry_counter = 0
            if vehicle_group:
                logging.root.level <= logging.TRACE and logging.trace(
                    ENTITY_PROCESSING_LOG_ENTRY.format(
                        f"Request transport for {entity.name} from {self.name} to {destination.name}",
                        DateTime.get(self.env.now)))
                entity.is_vehicle_routed = True
                VehicleManager().request_transport(vehicle_group, entity, destination, self, capa_id, event)
            else:
                destination.handle_entity_arrival(entity)

        #  If there is a routing expression, apply it
        if self.routing_expression:
            self.routing_expression[0](self, entity, *self.routing_expression[1:])

        if self.sequence_routing is False and self.routing_expression is None:
            # Get eligible connections that match the entity type
            eligible_connections = [
                (cumulative_probability, conn, vehicle)
                for cumulative_probability, (conn, vehicle) in self.connection_cache.items()
                if conn.entity_type is None or conn.entity_type == entity.entity_type
            ]

            logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
                "".join(["Eligible connections: ", str(eligible_connections)]), DateTime.get(self.env.now)))

            decision = random.uniform(0, 100)

            for cumulative_probability, connection, vehicle in eligible_connections:

                logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
                    "".join(["Decision: ", str(decision), ", Cumulative Probability: ", str(cumulative_probability)]), DateTime.get(self.env.now)))

                if decision <= cumulative_probability:
                    logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
                        "".join(["Entity ", entity.name, " routed to ", connection.next_component.name, " via vehicle ", vehicle.name if vehicle else 'None']), DateTime.get(self.env.now)))

                    if vehicle_group:
                        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"Request transport for {entity.name} from {self.name} to {connection.next_component.name}", DateTime.get(self.env.now)))
                        entity.is_vehicle_routed = True
                        VehicleManager().request_transport(vehicle_group, entity, connection.next_component, self, capa_id, event)
                    else:
                        connection.handle_entity_arrival(entity)
                    break

    def connect(self, next_server, probability: float = None, process_duration: float = None,
                entity_type: str = None, vehicle=None):

        from src.core.components.connection import Connection

        # Check for existing connection in Model's registry
        existing_connection = Model().get_connection(self.name, next_server.name)

        if existing_connection:
            connection = existing_connection
            connection.origin_component = self
            connection.next_component = next_server
            connection.probability = probability
            connection.process_duration = process_duration
            connection.entity_type = entity_type
            connection.vehicle = vehicle

            # Reinitialize process with new environment
            connection.reinitialize_process(self.env)

            self.connections[next_server.name] = connection
        else:
            # Create new connection
            connection = Connection(self.env, self, next_server, next_server.name,
                                    process_duration, probability, entity_type, vehicle)
            self.connections[next_server.name] = connection
            # Register the new connection in Model's registry
            Model().register_connection(self.name, next_server.name, connection)

        self.next_components.append((next_server, probability, entity_type, vehicle))
        self.update_connection_cache()

    def update_connection_cache(self):
        """
        Update the connection cache with the latest connections and probabilities.
        """
        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join(["Creating connection cache for ", str(self)]), DateTime.get(self.env.now)))
        self.connection_cache.clear()  # Clear existing cache to avoid stale entries
        total_probability = sum(probability for _, probability, _, _ in self.next_components if probability is not None)
        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join(["Total probability: ", str(total_probability)]), DateTime.get(self.env.now)))

        if total_probability == 0:
            num_components = len(self.next_components)
            equal_probability = 100 / num_components if num_components > 0 else 0
            cumulative_probability = 0
            for next_server, _, entity_type, vehicle in self.next_components:
                cumulative_probability += equal_probability
                logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
                    "".join(["Setting cache: ", str(cumulative_probability), " -> (", str(self.connections[next_server.name]), ", ", str(vehicle), ")"]), DateTime.get(self.env.now)))
                self.connection_cache[cumulative_probability] = (self.connections[next_server.name], vehicle)
        else:
            cumulative_probability = 0
            for next_server, probability, entity_type, vehicle in self.next_components:
                if probability is not None:
                    cumulative_probability += (probability / total_probability) * 100
                    logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
                        "".join(["Setting cache: ", str(cumulative_probability), " -> (", str(self.connections[next_server.name]), ", ", str(vehicle), ")"]), DateTime.get(self.env.now)))
                    self.connection_cache[cumulative_probability] = (self.connections[next_server.name], vehicle)

        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(
            "".join(["Updated connection cache: ", str(self.connection_cache)]), DateTime.get(self.env.now)))

    @staticmethod
    def retry(waiting_time, calling_object, entity: Entity, vehicle_group: str = None, capa_id=None, event=None):
        calling_object.retry_counter += 1
        if calling_object.retry_counter % 100 == 0:
            logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f'Retryed x{calling_object.retry_counter} at {calling_object.env.now} from {calling_object}', DateTime.get(calling_object.env.now)))
        yield calling_object.env.timeout(waiting_time)
        calling_object._route_without_truck(entity, vehicle_group=vehicle_group, capa_id=capa_id, event=event)

    def reset_routing(self):
        """
        Reset routing state. Called when component is reset between replications.
        """
        self.next_components = []
        self.number_exited = 0
        self.connection_cache.clear()
        self.connections.clear()
