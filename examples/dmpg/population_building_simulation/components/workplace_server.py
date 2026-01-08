from typing import Any
import simpy
from examples.dmpg.population_building_simulation.components.building_model import Building
from src.core.components.model import Model
from src.core.components.server import Server
from examples.dmpg.population_building_simulation.components.house_storage import House
from examples.dmpg.population_building_simulation.components.human_entity import Human
from examples.dmpg.population_building_simulation.config import (
    STAT_COMMUTES,
    STAT_WORK_TIME,
)


class Workplace(Server):
    """
    Workplace server: Pulls workers from queues during operating hours, processes them (work), and sends them home.
    """

    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        capacity: int,
        building: Building,
        **kwargs,
    ) -> None:
        self.building = building
        super().__init__(
            env=env,
            name=name,
            capacity=capacity,
            before_processing_trigger=self.on_work_start,
            after_processing_trigger=self.on_work_complete,
            **kwargs,
        )

    def on_work_start(self, server, entity: Human, **kwargs) -> bool:
        """
        Before-processing trigger: Called when worker arrives at workplace.
        Records the start time of the work shift and marks this day as worked.
        """

        if isinstance(entity, Human):
            entity.work_start_time = self.env.now
            # Mark which day the worker is working (to limit to 1 shift per day)
            current_day = int(self.env.now // (24 * 60))
            entity.last_work_day = current_day
        return True

    def on_work_complete(self, server, entity: Human, **kwargs: Any) -> bool:
        """
        After-processing trigger: Called when worker finishes their shift.

        Records work statistics and sends worker back home.
        """

        if entity.home_name:
            # Record work time statistic
            if entity.work_start_time is not None:
                work_duration = self.env.now - entity.work_start_time
                Model().record_tally_statistic(STAT_WORK_TIME, work_duration)
                Model().record_tally_statistic(STAT_COMMUTES, 1)  # Count this commute
                entity.work_start_time = None

            # Send worker home
            home: House = Model().get_component_by_name(entity.home_name)
            if home:
                home.handle_entity_arrival(entity)
                return False  # Don't use default routing
        return True
