import random
from typing import Any

from examples.dmpg.population_building_simulation.enums import AgeGroup
from src.core.components.entity import Entity


class Human(Entity):
    def __init__(
        self, name: str, creation_time: float, entity_type: str = "Human", **kwargs: Any
    ) -> None:
        super().__init__(name, creation_time, entity_type=entity_type, **kwargs)

        # Demographic attributes
        self.age: float = self._generate_age()
        self.gender: str = self._generate_gender()

        # Work tracking
        self.work_start_time: float | None = None
        self.last_work_day: int = -1  # Track the last day the worker worked

        # Location attributes
        self.home_name: str | None = None
        self.workplace_name: str | None = None

        # Status
        self.is_dead: bool = False

    def _generate_age(self) -> float:
        """
        Generate age using normal distribution (mean=40, std=18), clamped to 0-100.
        """

        age = float(int(random.gauss(40, 18)))
        return float(max(0, min(100, age)))

    def _generate_gender(self) -> str:
        """
        Generate gender with 50/50 distribution.
        """

        return "male" if random.random() < 0.5 else "female"

    def is_working_age(self) -> bool:
        """
        Check if person is of working age (18-65).
        """

        return 18 <= self.age < 65

    def reset(self) -> None:
        """
        Reset for entity pooling.
        """

        self.work_start_time = None

    def assign_home(self, index: int, amount_houses: int) -> int:
        house_idx = index % amount_houses
        self.home_name = f"House_{house_idx}"
        return house_idx

    @property
    def age_group(self) -> AgeGroup:
        if self.age < 18:
            return AgeGroup.CHILDREN
        elif self.age >= 65:
            return AgeGroup.RETIRED
        return AgeGroup.WORKING_AGE
