import simpy
from typing import Any
from examples.dmpg.population_building_simulation.components.human_entity import Human
from examples.dmpg.population_building_simulation.components.building_model import Building
from examples.dmpg.population_building_simulation import config
from src.core.components.logistic.storage import Storage
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.server import Server
from src.core.event.storage_event import StorageEvent


class House(Storage):
    """
    House storage: Holds citizens and routes workers to workplace queues.
    """

    MINUTES_PER_DAY = 24 * 60

    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        capacity: int,
        building: Building,
        **kwargs,
    ) -> None:
        self.building = building
        self.lat = building.lat
        self.lon = building.lon
        super().__init__(
            env,
            name=name,
            capacity=capacity,
            **kwargs,
        )
        self.storage_expression = (self.assign_to_workplace_queue,)
        self.routing_expression = (self.deliver_to_destination,)

    def assign_to_workplace_queue(self, entity: Human) -> str | None:
        """
        Storage expression: Routes workers to their workplace queue.

        Workers wait in their assigned workplace's queue until called.
        Non-workers (children, retirees) go to 'stay_home' queue which is never pulled currently.
        Workers who have already worked today return None (handled specially).
        """
        if (
            isinstance(entity, Human)
            and entity.is_working_age()
            and entity.workplace_name
        ):
            # Check if worker has already worked today (limit to 1 shift per day)
            current_day = int(self.env.now // self.MINUTES_PER_DAY)
            if entity.last_work_day == current_day:
                # Already worked today - return None to signal special handling
                return None
            return entity.workplace_name
        return "stay_home"

    def _process_entity(self, worker):
        """
        Override to handle workers who need to wait until the next day.
        """
        # Get entity from queue (same as parent)
        if not self.input_queue:
            return

        from src.core.types.queue_type import QueueType
        if self.queuing_order == QueueType.LIFO:
            entity, queue_entry_time = self.input_queue.pop()
        else:
            entity, queue_entry_time = self.input_queue.popleft()

        self.queue_length -= 1
        self.used_capacity += 1
        capa_id = self.capa_ids.popleft()

        # Check what queue the worker should go to
        if self.storage_expression:
            storage_queue = self.storage_expression[0](entity)

            if storage_queue is None:
                # Worker already worked today - schedule for next day
                self._schedule_next_day_work(entity)
                # Free up capacity immediately since we're not blocking
                self.used_capacity -= 1
                self.capa_ids.append(capa_id)
                return
            else:
                # Normal flow - add to queue and wait
                event = StorageEvent(self.env, entity)
                StorageManager.add_to_queue(storage_queue, event)
                yield event

        # Route the entity to its destination
        self.route_entity(entity, self.vehicle_group, capa_id)

        # Free up capacity
        self.used_capacity -= 1
        self.capa_ids.append(capa_id)

    def _schedule_next_day_work(self, entity: Human):
        """Schedule worker to be re-queued at the start of the next work day."""
        current_time = self.env.now
        current_day = int(current_time // self.MINUTES_PER_DAY)
        next_day_start = (current_day + 1) * self.MINUTES_PER_DAY + (config.WORK_START_HOUR * 60)
        delay = next_day_start - current_time

        self.env.process(self._delayed_requeue(entity, delay))

    def _delayed_requeue(self, entity: Human, delay: float):
        """Wait and then re-process the entity through the house."""
        yield self.env.timeout(delay)
        # Re-enter the house to go through the queue assignment again
        self.handle_entity_arrival(entity)

    def deliver_to_destination(
        self, component: Server, entity: Human, *args: Any
    ) -> None:
        """
        Routing expression: Delivers entity to destination set by pull system.

        When a workplace pulls a worker from the queue, the entity's destination
        is set by StorageManager. This function completes the delivery.
        """
        if entity.destination:
            entity.destination.handle_entity_arrival(entity)

