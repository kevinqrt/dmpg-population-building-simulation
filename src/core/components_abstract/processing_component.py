import logging
from abc import abstractmethod, ABC
from collections import deque
from typing import Callable, Tuple, Optional, Union

import numpy as np
import simpy

import src.core.global_imports as gi
import src.core.statistics.entity_type_utils as et
from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.model import Model, ComponentType
from src.core.components.work_schedule import WorkScheduleWeek, ask_work_schedule
from src.core.components_abstract.resetable_named_object import ResetAbleNamedObjectManager, ResetAbleNamedObject
from src.core.components_abstract.routing_object import RoutingObject
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.statistics.entity_type_utils import initialize_entity_types_component
from src.core.types.queue_type import QueueType
from src.core.utils.helper import get_value_from_distribution_with_parameters, validate_probabilities, \
    create_connection_cache, execute_trigger


class ProcessingComponent(ResetAbleNamedObject, RoutingObject, ABC):
    def __init__(self, env: simpy.Environment,
                 name: str,
                 component_type: ComponentType,
                 rnom: ResetAbleNamedObjectManager,
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

        super().__init__(env, name, component_type, rnom)

        Model().add_component(self, component_type)

        RoutingObject.__init__(self, env, routing_expression, sequence_routing)

        self.component_type = component_type
        self.processing_time_dwp = processing_time_distribution_with_parameters
        self.time_between_machine_breakdowns = time_between_machine_breakdowns
        self.machine_breakdown_duration = machine_breakdown_duration

        # SimPy Resource to manage concurrent processing slots
        self.capacity = capacity
        self.used_capacity = 0
        self.resource = simpy.Resource(env, capacity=self.capacity)

        # Queue management
        self.queuing_order = queuing_order
        self.input_queue = deque()
        self.queue_length = 0
        self.queue_lengths = []
        self.queue_times = []

        # Work schedule and oven setup
        self.work_schedule = work_schedule
        self.entity_processing_times = entity_processing_times or {}
        self.global_processing_times = global_processing_times

        # Add-on process triggers
        self.before_arrival_trigger = before_arrival_trigger
        self.after_arrival_trigger = after_arrival_trigger
        self.before_processing_trigger = before_processing_trigger
        self.after_processing_trigger = after_processing_trigger

        # Workforce planning: use the specified worker pool if provided.
        if worker_pool is not None:
            # Look up the worker pool by key in the model's worker_pools dictionary.
            self.worker_pool = worker_pool
            self.workers_required = workers_required
            pool_obj = Model().worker_pools.get(worker_pool, None)
            if pool_obj is None:
                raise ValueError(f"Worker pool '{worker_pool}' not found in Model().worker_pools")
            self.worker_store = pool_obj.store
        else:
            self.worker_store = None
            self.workers_required = 1

        # SimPy process management
        self.action = env.process(self.run())
        self.is_processing = env.event()

        # Internal server state
        self.initialized = False
        self.connection_cache = {}

        # Breakdown management
        if self.time_between_machine_breakdowns:
            self.time_until_next_machine_breakdown = (
                get_value_from_distribution_with_parameters(self.time_between_machine_breakdowns))

        # Storage management
        self.storage_queue = storage_queue
        self.storage_expression = storage_expression

        if self.storage_queue:
            for _ in range(self.capacity):
                if type(self.storage_queue) is list:
                    for entry in self.storage_queue:
                        StorageManager.release_next_entity(entry, (self, True))
                else:
                    StorageManager.release_next_entity(self.storage_queue, (self, False))  # add server to waiting pool

        # Capacity management
        self.capa_ids = deque([i for i in range(capacity)])
        self.block_event = {i: None for i in range(capacity)}

        # Vehicle management and coordinates
        self.vehicle_group = vehicle_group
        self.position = position

        self.entity_type_stats_component = {}

    def handle_entity_arrival(self, entity: Entity) -> None:
        """
        Handles the arrival of an entity, adding it to the queue and starting processing if applicable.
        """
        # Execute before_arrival_trigger
        if not execute_trigger(self.before_arrival_trigger, self, entity):
            # If trigger returns False, skip handling this entity
            return

        if gi.COLLECT_ENTITY_TYPE_STATS:
            initialize_entity_types_component(self.entity_type_stats_component, entity)

        if self.env.now >= gi.DURATION_WARM_UP:
            self.number_entered_pivot_table += 1

            if gi.COLLECT_ENTITY_TYPE_STATS:
                stats = self.entity_type_stats_component[entity.entity_type]
                stats[et.TOTAL_ENTITES_IN_QUEUE] += 1

        entity.current_location = self
        self.queue_length += 1

        if gi.COLLECT_ENTITY_TYPE_STATS:
            stats = self.entity_type_stats_component[entity.entity_type]
            stats[et.QUEUE_LENGTH] += 1
            stats[et.QUEUE_LENGTHS].append(stats[et.QUEUE_LENGTH])
            stats[et.MAX_ENTITES_IN_QUEUE] = max(stats[et.MAX_ENTITES_IN_QUEUE], stats[et.QUEUE_LENGTH])

        if self.env.now >= gi.DURATION_WARM_UP:
            self.queue_lengths.append(self.queue_length)

        self.input_queue.append((entity, self.env.now))

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(f"[{self.component_type}] {self.name} received entity {entity.name}",
                                               DateTime.get(self.env.now)))

        # Execute after_arrival_trigger
        execute_trigger(self.after_arrival_trigger, self, entity)

        self.env.process(self._request_worker())

    def _request_worker(self):
        """
        Processes entities from the queue if there is capacity and entities are available.
        """
        # Check if there's anything in the queue to process
        if not self.input_queue:
            return

        # Try to get a resource slot
        request = self.resource.request()
        yield request

        try:
            workers = []
            worker_locks = []
            worker_lock_requests = []

            if self.worker_store is not None:
                try:
                    # Ensure enough workers are available to avoid deadlock
                    if hasattr(self, 'workers_required') and self.workers_required > 1:
                        # Get current available workers
                        available_workers = len(self.worker_store.items)

                        # If not enough workers, release resource and return
                        if available_workers < self.workers_required:
                            # Not enough workers, skip processing for now
                            return

                    # For multiple workers - use a two-phase approach: first get all workers, then lock them
                    if hasattr(self, 'workers_required') and self.workers_required > 1:
                        # Phase 1: Get all required workers without locking
                        acquired_workers = []

                        # Get each worker one by one
                        for _ in range(self.workers_required):
                            # Get the first worker we find in the store
                            worker = yield self.worker_store.get()
                            acquired_workers.append(worker)

                        # Phase 2: Lock all workers
                        try:
                            for worker in acquired_workers:
                                worker_lock = Model().worker_pools[self.worker_pool].worker_locks[worker.capa_id]
                                worker_lock_request = worker_lock.request()
                                yield worker_lock_request

                                worker.start_assignment(self.name, self.env.now)

                                workers.append(worker)
                                worker_locks.append(worker_lock)
                                worker_lock_requests.append(worker_lock_request)

                            # Process the entity with multiple workers
                            yield from self._process_entity(workers)

                        except Exception as e:
                            for worker in acquired_workers:
                                if worker not in workers:
                                    yield self.worker_store.put(worker)
                            raise e

                    else:
                        # Single worker case
                        worker = yield self.worker_store.get()
                        worker_lock = Model().worker_pools[self.worker_pool].worker_locks[worker.capa_id]
                        worker_lock_request = worker_lock.request()
                        yield worker_lock_request

                        worker.start_assignment(self.name, self.env.now)
                        workers = [worker]
                        worker_locks = [worker_lock]
                        worker_lock_requests = [worker_lock_request]

                        yield from self._process_entity(worker)  # Pass the single worker, not a list

                finally:
                    # Release the worker lock
                    for worker_lock, worker_lock_request in zip(worker_locks, worker_lock_requests):
                        if worker_lock is not None and worker_lock_request is not None:
                            worker_lock.release(worker_lock_request)

                    # Release the worker
                    for worker in workers:
                        yield self.worker_store.put(worker)

            else:
                # If no worker store, process without a worker (pass None)
                yield from self._process_entity(None)

        finally:
            # Always release the resource
            self.resource.release(request)

    @abstractmethod
    def _process_entity(self, workers):
        pass

    def _handle_machine_breakdown(self, processing_time: float) -> None:
        """
        Simulates machine breakdowns during processing.
        """
        if processing_time > self.time_until_next_machine_breakdown:
            # (1) process until breakdown
            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(f"{self.name} machine breakdown",
                                                   DateTime.get(self.env.now)))

            yield self.env.timeout(self.time_until_next_machine_breakdown)

            # (2) Breakdown
            breakdown_duration = get_value_from_distribution_with_parameters(self.machine_breakdown_duration)
            yield self.env.timeout(breakdown_duration)

            # (3) Update downtime statistics
            if self.env.now >= gi.DURATION_WARM_UP:
                self.number_downtimes_pivot_table += 1
                self.total_downtime_pivot_table += breakdown_duration

            logging.root.level <= logging.TRACE and logging.trace(
                ENTITY_PROCESSING_LOG_ENTRY.format(f"{self.name} failure corrected",
                                                   DateTime.get(self.env.now)))

            # (4) Continue processing after breakdown is resolved
            processing_time_remaining = processing_time - self.time_until_next_machine_breakdown
            self.time_until_next_machine_breakdown = (
                get_value_from_distribution_with_parameters(self.time_between_machine_breakdowns))

            yield self.env.timeout(processing_time_remaining)

        else:
            yield self.env.timeout(processing_time)
            self.time_until_next_machine_breakdown -= processing_time

    def _determine_processing_time(self, entity: Entity):
        """Determine the correct processing time for the entity."""
        if self.entity_processing_times and entity.entity_type in self.entity_processing_times:
            return self.entity_processing_times[entity.entity_type]
        elif (self.global_processing_times and self.name in self.global_processing_times and
              entity.entity_type in self.global_processing_times[self.name]):
            return self.global_processing_times[self.name][entity.entity_type]
        else:
            return self.processing_time_dwp

    def run(self) -> simpy.Event:
        """
        Server's main processing loop, handling entity processing based on availability, resource capacity,
        and work schedule.
        """
        if not self.initialized:
            self._initialize_component()
            self.initialized = True

        while True:

            if self.input_queue and len(self.resource.users) < self.resource.capacity:
                self.env.process(self._request_worker())

            yield self.is_processing  # Wait for processing to be triggered by entity arrival

    def _initialize_component(self) -> None:
        """Perform initial setup tasks for the server, including validating probabilities."""
        create_connection_cache(self)
        validate_probabilities(self)

    def finalize_statistics_per_entity_type(self, sim_time):
        """
        Calculate final average values for per-entity-type queue stats.
        """
        for entity_type, stats in self.entity_type_stats_component.items():
            if stats[et.QUEUE_LENGTHS]:
                stats[et.AVG_ENTITES_IN_QUEUE] = np.mean(stats[et.QUEUE_LENGTHS])
            if stats[et.QUEUE_TIMES]:
                stats[et.AVG_TIME_IN_QUEUE] = np.mean(stats[et.QUEUE_TIMES])

    def get_next_entity_from_queue(self):
        if self.storage_queue and len(self.input_queue) == 0 and self.used_capacity < self.capacity:
            # Check work schedule - only pull during work hours
            if self.work_schedule is not None:
                is_active, time_to_wait, _ = ask_work_schedule(self.env.now, self.work_schedule)
                if not is_active:
                    # Outside work hours - schedule a delayed retry when work hours start
                    self.env.process(self._delayed_queue_check(time_to_wait))
                    return

            # Calculate how many entities we can still accept
            remaining_capacity = self.capacity - self.used_capacity

            if type(self.storage_queue) is list:
                # Pull as many entities as we have remaining capacity for, from any non-empty queue
                for _ in range(remaining_capacity):
                    pulled_from_any = False
                    for entry in self.storage_queue:
                        if not StorageManager.is_queue_empty(entry):
                            StorageManager.release_next_entity(entry, (self, False))
                            pulled_from_any = True
                            break  # Pull one entity per iteration, round-robin across queues
                    if not pulled_from_any:
                        # All queues are empty, register in waiting pool for all
                        for entry in self.storage_queue:
                            StorageManager.release_next_entity(entry, (self, True))
                        break
            else:
                # Pull as many entities as we have remaining capacity for
                for _ in range(remaining_capacity):
                    if StorageManager.is_queue_empty(self.storage_queue):
                        # Queue is empty, register in waiting pool and stop pulling
                        StorageManager.release_next_entity(self.storage_queue, (self, False))
                        break
                    else:
                        # Pull next entity from queue
                        StorageManager.release_next_entity(self.storage_queue, (self, False))

    def _delayed_queue_check(self, delay):
        """Wait until work hours start, then try to pull from queue."""
        yield self.env.timeout(delay)
        self.get_next_entity_from_queue()
