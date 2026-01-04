import logging
from typing import Optional, Union, Callable, Tuple

import simpy

import src.core.global_imports as gi
import src.core.statistics.entity_type_utils as et
from dmpg_logs.logging_utils.stats_logger import log_sink_statistics
from src.core.components.date_time import DateTime
from src.core.components.entity import EntityManager
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.model import Model, ComponentType
from src.core.components.source import Source
from src.core.components.work_schedule import WorkScheduleWeek
from src.core.components_abstract.processing_component import ProcessingComponent
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.statistics.entity_type_utils import initialize_entity_types_sink, update_entity_types_sink
from src.core.statistics.tally_statistic import TallyStatistic
from src.core.types.queue_type import QueueType
from src.core.utils.helper import execute_trigger, get_value_from_distribution_with_parameters, round_value


class Sink(ProcessingComponent):
    """
    A sink is a component where entities are destroyed, representing the end point in the simulation.
    """

    sinks = Model().get_component(ComponentType.SINKS)
    """
    A list of all the sinks in the simulation.
    """

    store_processed_entities: bool = False

    def __init__(self, env: simpy.Environment, name: str,
                 processing_time_distribution_with_parameters=None,  # Default the processing time is zero.
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
                 position: Tuple[float, float, float] = None,
                 addon_processing_done_method_with_parameters=None,
                 source: Source = None,
                 ):
        """
        Initialize a sink instance.

        :param env: SimPy environment.
        :param name: Name of the sink.
        :param addon_processing_done_method_with_parameters: Callable to be executed as an add-on process trigger.
        :param before_destruction_trigger: Function or tuple to be called before entity destruction.
        :param after_destruction_trigger: Function or tuple to be called after entity destruction.
        """
        ProcessingComponent.__init__(self, env,
                                     name,
                                     ComponentType.SINKS,
                                     Sink.sinks,
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

        """Callable method with parameters, called when entity processing is done."""
        self.addon_processing_done_method_with_parameters = addon_processing_done_method_with_parameters
        """Total number of entities processed by this sink."""
        self.tally_statistic = TallyStatistic()

        self.source = source
        self.processed_entities = []

    def reset(self):
        """
        Reset the sink state. Clears the list of processed entities and resets counters.
        """
        self.entities_processed = 0
        self.entity_type_stats_component.clear()

    def _process_entity(self, worker):
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
            ENTITY_PROCESSING_LOG_ENTRY.format(f"[Sink] {self.name} begins processing {worker_info}",
                                               DateTime.get(self.env.now)))

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[SinkStats] Sink={self.name}, Status=busy, Entity={entity.name} , NumberEntered={self.entities_processed} ", DateTime.get(self.env.now))
        )

        if gi.COLLECT_ENTITY_TYPE_STATS:
            initialize_entity_types_sink(self.entity_type_stats_component, entity)

        if self.env.now >= gi.DURATION_WARM_UP:
            time_in_system = self.env.now - entity.creation_time
            self.total_time_in_system += time_in_system
            self.max_time_in_system_pivot_table = max(self.max_time_in_system_pivot_table, time_in_system)
            self.min_time_in_system_pivot_table = min(self.min_time_in_system_pivot_table, time_in_system)

            if gi.COLLECT_ENTITY_TYPE_STATS:
                update_entity_types_sink(self.entity_type_stats_component, entity, time_in_system)

        # Process the entity
        if self.storage_queue:
            if type(self.storage_queue) is list:
                for entry in self.storage_queue:
                    StorageManager.remove_from_pool(entry, self)
            else:
                StorageManager.remove_from_pool(self.storage_queue, self)

        start_time = self.env.now
        # Process the entity
        if entity.is_vehicle_routed:
            entity.is_vehicle_routed = False
        else:
            self.used_capacity += 1

        capa_id = self.capa_ids.popleft()

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(f"[Sink] {self.name} starts processing {entity.name}",
                                               DateTime.get(start_time)))

        if self.processing_time_dwp:
            processing_time = get_value_from_distribution_with_parameters(self._determine_processing_time(entity))
        else:
            processing_time = 0
        resource_users = len(self.resource.users)

        # Simulate breakdowns or use ovens if applicable
        if self.time_between_machine_breakdowns:
            yield from self._handle_machine_breakdown(processing_time)
        else:
            yield self.env.timeout(processing_time)  # normal processing

        self.units_utilized_over_time.append((start_time, self.env.now, resource_users))

        # Log processing completion for this entity
        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[Sink] {self.name} finished processing {entity.name}, time {round_value(processing_time)}",
                DateTime.get(self.env.now)))

        if self.env.now >= gi.DURATION_WARM_UP:
            if self.units_utilized_over_time and self.units_utilized_over_time[-1][1] is None:
                last_start, _, units = self.units_utilized_over_time[-1]
                self.units_utilized_over_time[-1] = (last_start, self.env.now, units)

        # Execute after_processing_trigger
        if not execute_trigger(self.after_processing_trigger, self, entity, worker=worker, processing_time=processing_time):
            # If trigger returns False, skip routing the entity
            # Handle any custom logic as needed
            pass

        self.entities_processed += 1

        log_sink_statistics(self)

        entity.destruction_time = self.env.now

        if Sink.store_processed_entities:
            self.processed_entities.append(entity)

        EntityManager.remove_entity(entity)

        if self.addon_processing_done_method_with_parameters:
            self.addon_processing_done_method_with_parameters[0](self, entity,
                                                                 *self.addon_processing_done_method_with_parameters[1:])

            # If there's a Source instance given, generate a new entity
            if self.source:
                self.source.generate_single_entity()

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[Sink] {self.name} destroyed {entity.name} ", DateTime.get(self.env.now))
        )

        # Free up capacity
        self.used_capacity -= 1

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(
                f"[SinkStats] Sink={self.name}, Status=idle, Entity=-, NumberEntered={self.entities_processed}", DateTime.get(self.env.now))
        )

        # Return used capacity id
        self.capa_ids.append(capa_id)
