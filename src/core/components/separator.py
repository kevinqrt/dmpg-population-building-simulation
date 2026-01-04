import logging
from typing import Callable, Tuple, Optional, Union

import simpy

import src.core.global_imports as gi
import src.core.statistics.entity_type_utils as et
from dmpg_logs.logging_utils.stats_logger import log_separator_statistics
from src.core.event.block_event import BlockEvent
from src.core.components.date_time import DateTime
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.model import Model, ComponentType
from src.core.components.work_schedule import ask_work_schedule, WorkScheduleWeek
from src.core.components_abstract.processing_component import ProcessingComponent
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY, DURATION_WARM_UP
from src.core.types.queue_type import QueueType
from src.core.utils.helper import get_value_from_distribution_with_parameters, round_value, execute_trigger


class Separator(ProcessingComponent):
    """
    Simulates a seperator within a discrete event simulation environment.

    This seperator processes entities based on specified parameters, such as
    processing time distributions, machine breakdown schedules, work schedules,
    and queuing order. It supports tracking of various metrics, including processing
    times, downtimes, and the number of entities processed.
    """

    separators = Model().get_component(ComponentType.SEPARATORS)

    """Manages all existing seperator instances."""

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
                 storage_queue: str | list[str] = None,
                 storage_expression=None,
                 sequence_routing: bool = False,
                 worker_pool: Optional[str] = None,
                 workers_required: int = 1,
                 before_arrival_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 after_arrival_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 before_processing_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 after_processing_trigger: Optional[Union[Callable, Tuple[Callable, ...]]] = None,
                 vehicle_group: str = None,
                 position: Tuple[float, float, float] = None
                 ):
        """
       :param env: simpy environment
       :param name: separator identification for logging / pivot table
       :param processing_time_distribution_with_parameters:
       :param time_between_machine_breakdowns: Time between machine breakdowns
       :param machine_breakdown_duration: Duration of the machine breakdown
       :param queuing_order: e.g., FIFO
       :param sequence_routing: whether sequence routing is used for the outgoing connection or not
       """
        ProcessingComponent.__init__(self, env,
                                     name,
                                     ComponentType.SEPARATORS,
                                     Separator.separators,
                                     processing_time_distribution_with_parameters,
                                     capacity,
                                     time_between_machine_breakdowns,
                                     machine_breakdown_duration,
                                     work_schedule,
                                     queuing_order,
                                     routing_expression,
                                     entity_processing_times,
                                     global_processing_times,
                                     storage_queue,
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
        Processes entities from the queue if there is capacity and entities are available.
        """
        if self.work_schedule:
            active, time_to_wait, _ = ask_work_schedule(self.env.now, self.work_schedule)

            if not active:
                yield self.env.timeout(time_to_wait)

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
        if self.env.now >= DURATION_WARM_UP:
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
                ENTITY_PROCESSING_LOG_ENTRY.format(f"[Separator] {self.name} begins processing {entity.name} , worker={worker_info}",
                                                   DateTime.get(self.env.now)))

            # Log statistics before processing
            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(
                    f"[SeparatorStats] Separator={self.name}, Status=busy, Entity={entity.name}, Queue={self.queue_length}, Total={self.total_entities_processed_pivot_table}",
                    DateTime.get(self.env.now)
                )
            )

            # Process the entity
            if self.storage_queue:
                if type(self.storage_queue) is list:
                    for entry in self.storage_queue:
                        StorageManager.remove_from_pool(entry, self)
                else:
                    StorageManager.remove_from_pool(self.storage_queue, self)

            start_time = self.env.now

            if entity.is_vehicle_routed:
                entity.is_vehicle_routed = False
            else:
                self.used_capacity += 1

            capa_id = self.capa_ids.popleft()

            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(f"[Separator] {self.name} starts processing {entity.name}",
                                                   DateTime.get(start_time)))

            processing_time = get_value_from_distribution_with_parameters(self._determine_processing_time(entity))
            resource_users = len(self.resource.users)

            # Set current location for entity (from first file)
            entity.current_location = self
            number_members = len(entity.batch_members)

            # Route and set location for batch members
            for member in entity.batch_members:
                member.current_location = self
                self.route_entity(member, self.vehicle_group, capa_id)
            entity.batch_members = []

            if self.time_between_machine_breakdowns:
                yield from self._handle_machine_breakdown(processing_time)
            else:
                yield self.env.timeout(processing_time)  # normal processing

            self.units_utilized_over_time.append((start_time, self.env.now, resource_users))

            # Log processing completion for this entity.
            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(
                    f"[Separator] {self.name} finished processing {entity.name} time {round_value(processing_time)}",
                    DateTime.get(self.env.now)))

            if self.env.now >= DURATION_WARM_UP:
                if self.units_utilized_over_time and self.units_utilized_over_time[-1][1] is None:
                    last_start, _, units = self.units_utilized_over_time[-1]
                    self.units_utilized_over_time[-1] = (last_start, self.env.now, units)

                self.total_entities_processed_pivot_table += 1
                self.total_processing_time_pivot_table += processing_time
                self.number_parents_exited_pivot_table += 1
                self.number_members_exited_pivot_table = number_members

                if gi.COLLECT_ENTITY_TYPE_STATS:
                    stats = self.entity_type_stats_component[entity.entity_type]
                    stats[et.ENTITIES_PROCESSED] += 1
                    stats[et.TOTAL_TIME_PROCESSING] += processing_time
                    stats[et.AVG_TIME_PROCESSING] = stats[et.TOTAL_TIME_PROCESSING] / stats[et.ENTITIES_PROCESSED]

                # Log statistics after processing
                logging.root.level <= logging.TRACE and logging.trace(
                    ENTITY_PROCESSING_LOG_ENTRY.format(
                        f"[SeparatorStats] Separator={self.name}, Status=idle, Entity=-, Queue={self.queue_length}, Total={self.total_entities_processed_pivot_table}",
                        DateTime.get(self.env.now)
                    )
                )

            # Log server statistics (from first file)
            effective_time = max(0.0, self.env.now - DURATION_WARM_UP)
            log_separator_statistics(self, effective_time=effective_time, total_time=self.env.now)

            # Route entity to next destination
            self.route_entity(entity, self.vehicle_group, capa_id)

            # Handeling from block states until the block condition is removed
            if type(self.block_event[capa_id]) is BlockEvent:
                yield self.block_event[capa_id]
                self.block_event[capa_id] = None

            # Free up capacity
            self.used_capacity -= 1

            # Return used capacity id
            self.capa_ids.append(capa_id)

        self.get_next_entity_from_queue()

    def reset(self) -> None:
        """Reset the Seperator's state and statistics."""
        self.input_queue.clear()
        self.queue_lengths = []
        self.queue_times = []
        self.queue_length = 0
        self.total_entities_processed_pivot_table = 0
        self.total_processing_time_pivot_table = 0
        self.number_entered_pivot_table = 0
        self.number_members_exited_pivot_table = 0
        self.number_parents_exited_pivot_table = 0
        self.units_allocated_pivot_table = 0
        self.units_utilized_pivot_table = 0
        self.total_downtime_pivot_table = 0
        self.number_downtimes_pivot_table = 0
        self.uptime_pivot_table = 0
        self.total_uptime_pivot_table = 0
        self.number_uptimes_pivot_table = 0
        self.units_utilized_over_time = []
        if self.time_between_machine_breakdowns:
            self.time_until_next_machine_breakdown = (
                get_value_from_distribution_with_parameters(self.time_between_machine_breakdowns))
