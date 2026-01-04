import logging
from typing import Callable, Optional, Tuple, Union

import simpy

import src.core.global_imports as gi
import src.core.statistics.entity_type_utils as et
from dmpg_logs.logging_utils.stats_logger import log_combiner_statistics
from src.core.event.block_event import BlockEvent
from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.model import Model, ComponentType
from src.core.components.work_schedule import ask_work_schedule, WorkScheduleWeek
from src.core.components_abstract.processing_component import ProcessingComponent
from src.core.global_imports import DURATION_WARM_UP
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.statistics.entity_type_utils import initialize_entity_types_combiner
from src.core.types.queue_type import QueueType
from src.core.utils.helper import count_entity_type, get_entity_by_type
from src.core.utils.helper import get_value_from_distribution_with_parameters, round_value


class Combiner(ProcessingComponent):
    """Represents a combiner in a simulation environment"""

    combiners = Model().get_component(ComponentType.COMBINER)
    """List of all existing combiner instances"""

    def __init__(self, env: simpy.Environment, name: str,
                 processing_time_distribution_with_parameters=None,
                 capacity: int = 1,
                 members_to_combine: int = 1,
                 combination_rules: dict = None,
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
          :param env: SimPy environment
          :param name: Server name for identification/logging
          :param processing_time_distribution_with_parameters: Distribution and parameters for processing time
          :param capacity: Number of concurrent processing Servers
          :param time_between_machine_breakdowns: Time between machine breakdowns
          :param machine_breakdown_duration: Duration of breakdowns
          :param work_schedule: Work schedule for the server
          :param queuing_order: Queue order (FIFO, LIFO) for processing
          :param routing_expression: Routing logic for processed entities
          :param entity_processing_times: Dictionary of entity types and their specific processing times
          :param global_processing_times: Global processing times dictionary (server name -> entity type -> times)
          :param oven: Optional oven object to simulate heating/cooling processes
          :param use_storage: Should a storage system be used
          :param storage_queue: The queue from which the server pulls its entities
          :param storage_expression: Complex logic to manage multiple queues and entities
          :param sequence_routing: Whether sequence routing is used for the outgoing connection or not
          :param worker_pool: Name of the worker pool to use
          :param workers_required: Number of workers required for processing (default: 1)
          :param before_arrival_trigger: Function or tuple to be called before entity arrival
          :param after_arrival_trigger: Function or tuple to be called after entity arrival
          :param before_processing_trigger: Function or tuple to be called before entity processing
          :param after_processing_trigger: Function or tuple to be called after entity processing
        """
        ProcessingComponent.__init__(self, env,
                                     name,
                                     ComponentType.COMBINER,
                                     Combiner.combiners,
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

        self.member_input_queue = []
        self.member_queue_length = 0
        self.member_queue_lengths = []
        self.member_queue_times = []

        self.total_queue_length = 0

        # Combiner logic
        self.members_to_combine = members_to_combine
        self.combination_rules = combination_rules

    def handle_entity_arrival(self, entity: Entity) -> None:
        """
        Handles the arrival of an entity, adding it to the queue and starting processing if applicable.
        """
        if gi.COLLECT_ENTITY_TYPE_STATS:
            initialize_entity_types_combiner(self.entity_type_stats_component, entity)
            stats = self.entity_type_stats_component[entity.entity_type]
            stats[et.ENTITIES_IN_QUEUE_TOTAL] += 1

        self.total_queue_length += 1
        entity.current_location = self

        if self.env.now >= DURATION_WARM_UP:
            if entity.is_parent:
                self.number_parents_entered_pivot_table += 1
                if gi.COLLECT_ENTITY_TYPE_STATS:
                    stats = self.entity_type_stats_component[entity.entity_type]
                    stats[et.PARENTS_ENTERED] += 1
            else:
                self.number_members_entered_pivot_table += 1
                if gi.COLLECT_ENTITY_TYPE_STATS:
                    stats = self.entity_type_stats_component[entity.entity_type]
                    stats[et.MEMBERS_ENTERED] += 1

        if entity.is_parent:
            self.queue_length += 1
            self.queue_lengths.append(self.queue_length)
            self.input_queue.append((entity, self.env.now))
            if gi.COLLECT_ENTITY_TYPE_STATS:
                stats = self.entity_type_stats_component[entity.entity_type]
                stats[et.PARENTS_QUEUE_LENGTH] += 1
                stats[et.PARENTS_QUEUE_LENGTHS].append(stats[et.PARENTS_QUEUE_LENGTH])
                stats[et.PARENTS_IN_QUEUE_MAX] = max(stats[et.PARENTS_IN_QUEUE_MAX], stats[et.PARENTS_QUEUE_LENGTH])
        else:
            self.member_queue_length += 1
            self.member_queue_lengths.append(self.member_queue_length)
            self.member_input_queue.append((entity, self.env.now))
            if gi.COLLECT_ENTITY_TYPE_STATS:
                stats = self.entity_type_stats_component[entity.entity_type]
                stats[et.MEMBERS_QUEUE_LENGTH] += 1
                stats[et.MEMBERS_QUEUE_LENGTHS].append(stats[et.MEMBERS_QUEUE_LENGTH])
                stats[et.MEMBERS_IN_QUEUE_MAX] = max(stats[et.MEMBERS_IN_QUEUE_MAX], stats[et.MEMBERS_QUEUE_LENGTH])

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(f"[Combiner] {self.name} received entity {entity.name}",
                                               DateTime.get(self.env.now)))

        self.env.process(self._request_worker())

    def _process_entity(self, worker):
        """
        Processes entities from the queue if there is capacity and entities are available.
        """
        if self.work_schedule:
            active, time_to_wait, _ = ask_work_schedule(self.env.now, self.work_schedule)

            if not active:
                yield self.env.timeout(time_to_wait)

        # Add log info about workers if applicable
        worker_info = ""
        if isinstance(worker, list) and worker:
            worker_info = f" with {len(worker)} workers"
        elif worker is not None:
            worker_info = f" with worker {worker.id}"

        members_poped = 0
        member_entry_times = []
        combination_possibile = False

        if self.combination_rules:
            # Check whether a rule can be fulfilled or not
            for rule in self.combination_rules:
                if self.input_queue and count_entity_type(rule, self.member_input_queue) >= self.combination_rules[rule]:  # rule fulffilled
                    entity, queue_entry_time = self.input_queue.popleft()

                    for _ in range(self.combination_rules[rule]):
                        member, member_queue_entry_time = get_entity_by_type(rule, self.member_input_queue)
                        member_entry_times.append(member_queue_entry_time)
                        entity.batch_members.append(member)
                        members_poped += 1

                    combination_possibile = True
        else:
            if self.input_queue and (len(self.member_input_queue) >= self.members_to_combine):
                # Get entity to process based on queue order.
                if self.queuing_order == QueueType.LIFO:
                    entity, queue_entry_time = self.input_queue.pop()
                    for _ in range(self.members_to_combine):
                        member, member_queue_entry_time = self.member_input_queue.pop(-1)
                        member_entry_times.append(member_queue_entry_time)
                        entity.batch_members.append(member)
                        members_poped += 1

                else:  # default: FIFO
                    entity, queue_entry_time = self.input_queue.popleft()
                    for _ in range(self.members_to_combine):
                        member, member_queue_entry_time = self.member_input_queue.pop()
                        member_entry_times.append(member_queue_entry_time)
                        entity.batch_members.append(member)
                        members_poped += 1

                combination_possibile = True

        if combination_possibile:
            # Track entities being processed and queue timing.
            self.queue_length -= 1
            self.queue_times.append(self.env.now - queue_entry_time)

            # EntityType-spezifische QueueStats aktualisieren
            if entity.entity_type in self.entity_type_stats_component:
                stats = self.entity_type_stats_component[entity.entity_type]
                stats[et.PARENTS_QUEUE_LENGTH] -= 1
                stats[et.PARENTS_QUEUE_TIMES].append(queue_entry_time)
                stats[et.PARENTS_TIME_IN_QUEUE_MAX] = max(stats[et.PARENTS_TIME_IN_QUEUE_MAX], queue_entry_time)

                stats[et.MEMBERS_QUEUE_LENGTH] -= members_poped
                for i in range(members_poped):
                    stats[et.MEMBERS_QUEUE_TIMES].append(self.env.now - member_entry_times[i])
                    stats[et.MEMBERS_TIME_IN_QUEUE_MAX] = max(stats[et.MEMBERS_TIME_IN_QUEUE_MAX], queue_entry_time)

            self.member_queue_length -= members_poped
            for i in range(members_poped):
                self.member_queue_times.append(self.env.now - member_entry_times[i])

            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(f"[Combiner] {self.name} begins processing {entity.name} , worker={worker_info}",
                                                   DateTime.get(self.env.now)))

            # Processes a single entity logic.
            if self.storage_queue:
                StorageManager.remove_from_pool(self.storage_queue, self)

            start_time = self.env.now

            if entity.is_vehicle_routed:
                entity.is_vehicle_routed = False
            else:
                self.used_capacity += 1

            capa_id = self.capa_ids.popleft()

            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(f"[Combiner] {self.name} starts processing {entity.name}",
                                                   DateTime.get(start_time)))

            # Log statistics before processing (from first file)
            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(
                    f"[CombinerStats] Combiner={self.name}, Status=busy, Entity={entity.name}, Queue={self.queue_length}, Total={self.total_entities_processed_pivot_table}",
                    DateTime.get(self.env.now)
                )
            )

            processing_time = get_value_from_distribution_with_parameters(self._determine_processing_time(entity))
            resource_users = len(self.resource.users)

            # Simulate breakdowns or use ovens if applicable.
            if self.time_between_machine_breakdowns:
                yield from self._handle_machine_breakdown(processing_time)
            else:
                yield self.env.timeout(processing_time)  # normal processing

            self.units_utilized_over_time.append((start_time, self.env.now, resource_users))

            # Log processing completion for this entity.
            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(
                    f"[Combiner] {self.name} finished processing {entity.name} time {round_value(processing_time)}",
                    DateTime.get(self.env.now)))

            if self.env.now >= DURATION_WARM_UP:
                if self.units_utilized_over_time and self.units_utilized_over_time[-1][1] is None:
                    last_start, _, units = self.units_utilized_over_time[-1]
                    self.units_utilized_over_time[-1] = (last_start, self.env.now, units)

                self.total_entities_processed_pivot_table += 1
                self.total_processing_time_pivot_table += processing_time
                self.number_combinded_exited_pivot_table += 1

                if gi.COLLECT_ENTITY_TYPE_STATS:
                    stats = self.entity_type_stats_component[entity.entity_type]
                    stats[et.ENTITIES_PROCESSED] += 1
                    stats[et.TOTAL_TIME_PROCESSING] += processing_time
                    stats[et.AVG_TIME_PROCESSING] = stats[et.TOTAL_TIME_PROCESSING] / stats[et.ENTITIES_PROCESSED]

                effective_time = max(0.0, self.env.now - gi.DURATION_WARM_UP)
                log_combiner_statistics(self, effective_time=effective_time, total_time=self.env.now)

                # Log statistics after processing (from first file)
                logging.root.level <= logging.TRACE and logging.trace(
                    ENTITY_PROCESSING_LOG_ENTRY.format(
                        f"[CombinerStats] Combiner={self.name}, Status=idle, Entity=-, Queue={self.queue_length}, Total={self.total_entities_processed_pivot_table}",
                        DateTime.get(self.env.now)
                    )
                )

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
        """Reset the server's state and statistics."""
        self.input_queue.clear()
        self.queue_length = 0
        self.queue_lengths = []
        self.queue_times = []
        self.member_input_queue.clear()
        self.member_queue_lengths = []
        self.member_queue_times = []
        self.member_queue_length = 0
        self.total_entities_processed_pivot_table = 0
        self.total_processing_time_pivot_table = 0
        self.number_parents_entered_pivot_table = 0
        self.number_members_entered_pivot_table = 0
        self.number_combinded_exited_pivot_table = 0
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
