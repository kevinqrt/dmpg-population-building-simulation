import logging
from typing import Tuple, Optional, Callable, Union

import simpy

import src.core.global_imports as gi
import src.core.statistics.entity_type_utils as et
from dmpg_logs.logging_utils.stats_logger import log_storage_statistics
from src.core.event.block_event import BlockEvent
from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.model import Model, ComponentType
from src.core.components.work_schedule import WorkScheduleWeek
from src.core.components_abstract.processing_component import ProcessingComponent
from src.core.event.storage_event import StorageEvent
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.types.queue_type import QueueType
from src.core.utils.helper import get_value_from_distribution_with_parameters, round_value, \
    execute_trigger


class Storage(ProcessingComponent):
    """
    Simulates a storage within a discrete event simulation environment.

    This storage processing entities based on specified parameters, such as
    processing time distributions or release events. It supports tracking of
    various metrics, including processing times, and the number of entities
    processed.
    """

    storages = Model().get_component(ComponentType.STORAGE)
    """Manages all existing storage instances."""

    def __init__(self, env: simpy.Environment, name: str,
                 processing_time_distribution_with_parameters=None,
                 capacity: int = 1,
                 time_between_machine_breakdowns: Optional[Tuple[Callable, ...]] = None,
                 machine_breakdown_duration: Optional[Tuple[Callable, ...]] = None,
                 work_schedule: WorkScheduleWeek = None,
                 queuing_order: QueueType = QueueType.FIFO,
                 routing_expression=None,
                 entity_processing_times=None,
                 global_processing_times=None,
                 storage_expression=None,
                 sequence_routing: bool = False,
                 worker_pool: Optional[str] = None,
                 workers_required: int = 1,
                 before_arrival_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 after_arrival_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 before_processing_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 after_processing_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 vehicle_group: str = None,
                 position: Tuple[float, float, float] = None):
        """
        :param env: SimPy environment
        :param name: Storage name for identification/logging
        :param processing_time_distribution_with_parameters: Distribution and parameters for processing time
        :param resource_capacity: Number of concurrent processing Servers
        :param queuing_order: Queue order (FIFO, LIFO) for processing
        :param routing_expression: Routing logic for processed entities
        :param entity_processing_times: Dictionary of entity types and their specific processing times
        :param global_processing_times: Global processing times dictionary (storage name -> entity type -> times)
        :param storage_expression: Logic to place the entities in the storage queues
        """

        ProcessingComponent.__init__(self, env,
                                     name,
                                     ComponentType.STORAGE,
                                     Storage.storages,
                                     processing_time_distribution_with_parameters,
                                     capacity,
                                     time_between_machine_breakdowns,
                                     machine_breakdown_duration,
                                     work_schedule,
                                     queuing_order,
                                     routing_expression,
                                     entity_processing_times,
                                     global_processing_times,
                                     None,
                                     storage_expression,
                                     sequence_routing,
                                     worker_pool,
                                     workers_required,
                                     before_arrival_trigger,
                                     after_arrival_trigger,
                                     before_processing_trigger,
                                     after_processing_trigger,
                                     vehicle_group,
                                     position)

    def _process_entity(self, worker):
        """
        Process an entity.

        :param worker: A worker, list of workers, or None
        """

        # Check if queue is empty - this handles race conditions
        if not self.input_queue:
            return

        # Get entity to process based on queue order
        if self.queuing_order == QueueType.LIFO:
            entity, queue_entry_time = self.input_queue.pop()
        else:  # default: FIFO
            entity, queue_entry_time = self.input_queue.popleft()

        # Execute before_processing_trigger
        if not execute_trigger(self.before_processing_trigger, self, entity, worker=worker):
            # If trigger returns False, skip processing this entity
            # Put the entity back in queue or handle as needed
            self.input_queue.appendleft((entity, queue_entry_time))
            return

        # Track queue stats
        self.queue_length -= 1
        if self.env.now >= gi.DURATION_WARM_UP:
            self.queue_times.append(self.env.now - queue_entry_time)

            if gi.COLLECT_ENTITY_TYPE_STATS:
                # Track entities being processed and queue timing.
                time_in_queue = self.env.now - queue_entry_time

                # EntityType-spezifische QueueStats aktualisieren
                if entity.entity_type in self.entity_type_stats_component:
                    stats = self.entity_type_stats_component[entity.entity_type]
                    stats[et.QUEUE_LENGTH] -= 1
                    stats[et.QUEUE_TIMES].append(time_in_queue)
                    stats[et.MAX_TIME_IN_QUEUE] = max(stats[et.MAX_TIME_IN_QUEUE], time_in_queue)

        # Add log info about workers if applicable
        worker_info = ""
        if isinstance(worker, list) and worker:
            worker_info = f" with {len(worker)} workers"
        elif worker is not None:
            worker_info = f" with worker {worker.id}"

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(f"[Storage] {self.name} begins processing {entity.name} , worker={worker_info}",
                                               DateTime.get(self.env.now)))

        start_time = self.env.now
        processing_time = 0  # Will be calculated if processing_time_dwp is set, or measured as elapsed time

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[StorageStats] Storage={self.name}, Status=busy, Entity={entity.name} Queue={self.queue_length}, Total={self.total_entities_processed_pivot_table}",
                DateTime.get(self.env.now)
            )
        )

        if entity.is_vehicle_routed:
            entity.is_vehicle_routed = False
        else:
            self.used_capacity += 1

        capa_id = self.capa_ids.popleft()

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(f"[Storage] {self.name} starts processing {entity.name}",
                                               DateTime.get(start_time)))

        # Start tracking utilization with the current count of processing entities
        if not self.units_utilized_over_time or self.units_utilized_over_time[-1][1] is not None:
            self.units_utilized_over_time.append((start_time, None, len(self.resource.users)))

        if self.processing_time_dwp:
            processing_time_dwp = self._determine_processing_time(entity)
            processing_time = get_value_from_distribution_with_parameters(processing_time_dwp)
            yield self.env.timeout(processing_time)  # Time-based storing

        if self.storage_expression:
            storage_queue = self.storage_expression[0](entity)

            event = StorageEvent(self.env, entity)  # creates event
            StorageManager.add_to_queue(storage_queue, event)  # handles the storing of entity
            yield event

        if gi.COLLECT_ENTITY_TYPE_STATS:
            stats = self.entity_type_stats_component[entity.entity_type]
            stats[et.ENTITIES_PROCESSED] += 1
            stats[et.TOTAL_TIME_PROCESSING] += processing_time
            stats[et.AVG_TIME_PROCESSING] = stats[et.TOTAL_TIME_PROCESSING] / stats[et.ENTITIES_PROCESSED]

        end_time = self.env.now

        processing_time = end_time - start_time

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[Storage] {self.name} finished processing {entity.name} time {round_value(processing_time)}",
                DateTime.get(self.env.now)))

        if end_time >= gi.DURATION_WARM_UP:

            if self.units_utilized_over_time and self.units_utilized_over_time[-1][1] is None:
                last_start, _, units = self.units_utilized_over_time[-1]
                self.units_utilized_over_time[-1] = (last_start, end_time, units)

            self.total_entities_processed_pivot_table += 1
            self.total_processing_time_pivot_table += processing_time
            self.number_exited_pivot_table += 1

        effective_time = max(0.0, self.env.now - gi.DURATION_WARM_UP)
        #log_storage_statistics(self, effective_time=effective_time, total_time=self.env.now)

        # Execute after_processing_trigger
        if not execute_trigger(self.after_processing_trigger, self, entity, worker=worker, processing_time=processing_time):
            # If trigger returns False, skip routing the entity
            pass
        else:
            # Route the entity to its next destination
            self.route_entity(entity, self.vehicle_group, capa_id)

        # Handeling from block states until the block condition is removed
        if type(self.block_event[capa_id]) is BlockEvent:
            yield self.block_event[capa_id]
            self.block_event[capa_id] = None

        # Free up capacity
        self.used_capacity -= 1

        # Return used capacity id
        self.capa_ids.append(capa_id)

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[StorageStats] Storage={self.name}, Status=idle, Entity=-, Queue={self.queue_length}, Total={self.total_entities_processed_pivot_table}",
                DateTime.get(self.env.now)
            )
        )

    def _determine_processing_time(self, entity: Entity):
        """Determine the correct processing time for the entity."""
        if self.entity_processing_times and entity.entity_type in self.entity_processing_times:
            return self.entity_processing_times[entity.entity_type]
        elif (self.global_processing_times and self.name in self.global_processing_times and entity.entity_type in
              self.global_processing_times[self.name]):
            return self.global_processing_times[self.name][entity.entity_type]
        else:
            return self.processing_time_dwp

    def reset(self):
        """Reset the storage's state and statistics."""
        self.input_queue.clear()
        self.queue_lengths = []
        self.queue_times = []
        self.queue_length = 0
        self.total_entities_processed_pivot_table = 0
        self.total_processing_time_pivot_table = 0
        self.number_entered_pivot_table = 0
        self.number_exited_pivot_table = 0
        self.units_allocated_pivot_table = 0
        self.units_utilized_pivot_table = 0
        self.units_utilized_over_time = []
