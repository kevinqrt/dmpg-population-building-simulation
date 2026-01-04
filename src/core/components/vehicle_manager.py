import logging
from typing import Tuple, Callable

from src.core.components.exception import MissingVehicleException
from src.core.components.date_time import DateTime
from src.core.components.vehicle_manager_strategy import get_vehicle_with_lowest_queue
from src.core.components_abstract.singleton import Singleton
from src.core.event.block_event import BlockEvent
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.utils.utils import calc_upper_and_lower_bound


class VehicleManager(metaclass=Singleton):
    def __init__(self):
        self.vehicle_groups = {}
        self.vehicle_group_strategies = {}
        self.vehicle_queues = {}
        self.env = None
        self.set_bounds = False

        self.add_vehicle_group('DefaultVehicleGroup')

    def add_vehicle_group(self, group_name: str, strategy: Tuple[Callable, ...] = None):
        self.vehicle_groups[group_name] = []
        self.vehicle_queues[group_name] = []
        if strategy:
            self.vehicle_group_strategies[group_name] = strategy
        else:
            self.vehicle_group_strategies[group_name] = (get_vehicle_with_lowest_queue,)

    def add_vehicle_to_group(self, group_name: str, vehicle):
        if vehicle is None:
            raise MissingVehicleException('Vehicle must be provided')

        self.vehicle_groups[group_name].append(vehicle)

    def _transport_entity(self, vehicle, entity, destination, calling_object, event):
        if self.set_bounds:
            vehicle.lower_bound, vehicle.upper_bound = calc_upper_and_lower_bound(vehicle, calling_object, destination)
        yield self.env.process(vehicle.move_to_location(calling_object))
        self.env.schedule(event)
        logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"Transported {entity.name} from {calling_object.name} to {destination.name}", DateTime.get(self.env.now)))
        vehicle.handle_entity_arrival(entity, destination)

    def request_transport(self, group_name: str, entity, destination, calling_object, capa_id=None, event=None):
        if event is None:
            event = BlockEvent(self.env)  # Blocking the station until the entity is transported
            calling_object.block_event[capa_id] = event

        if len(self.vehicle_queues[group_name]) == 0:
            logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"Vehicle queue {group_name} is empty!", DateTime.get(self.env.now)))
            vehicle = self._get_vehicle_from_group(group_name, entity, calling_object, destination)
        else:
            vehicle = None
            logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"Vehicle queue {group_name} is not empty!", DateTime.get(self.env.now)))
            for vehicle in self.vehicle_groups[group_name]:
                if vehicle.idle:
                    logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"{vehicle.name} is idle request entity", DateTime.get(self.env.now)))
                    self.request_entity(group_name, vehicle)

        if vehicle is None:
            logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"No vehicle available adding {entity.name} to {group_name}", DateTime.get(self.env.now)))
            # no vehicle availble put entity in queue
            self.vehicle_queues[group_name].append((entity, destination, calling_object, event, self.env.now))
        else:
            logging.root.level <= logging.TRACE and logging.trace(ENTITY_PROCESSING_LOG_ENTRY.format(f"Vehicle available transporting {entity.name}", DateTime.get(self.env.now)))
            self.env.process(self._transport_entity(vehicle, entity, destination, calling_object, event))

    def _get_vehicle_from_group(self, group_name: str, entity, calling_object, destination):
        return self.vehicle_group_strategies[group_name][0](self.vehicle_groups[group_name], calling_object, entity, destination)

    def request_entity(self, group_name: str, vehicle):
        event_found = False
        index = -1

        if len(self.vehicle_queues[group_name]) > 0:

            while not event_found:
                index = index + 1
                transport_req = self.vehicle_queues[group_name][index]
                """
                if waiting_time > 1:
                    event_found = True
                    print(f'Waited to be transproted for: {self.env.now - transport_req[4]}')
                """
                vehilce = self._get_vehicle_from_group(group_name, transport_req[0], transport_req[1], transport_req[2])
                if vehilce == vehilce:
                    event_found = True

        else:
            self.env.process(vehicle.return_to_home())

        if event_found:
            transport_req = self.vehicle_queues[group_name].pop(index)
            self.env.process(self._transport_entity(vehicle, transport_req[0], transport_req[1], transport_req[2], transport_req[3]))
        else:
            self.env.process(vehicle.return_to_home())
