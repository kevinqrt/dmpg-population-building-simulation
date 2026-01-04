from collections import defaultdict
from typing import Union, Optional, List, Dict
from simpy import Environment

import src.core.global_imports as gi
from src.core.components_abstract.singleton import Singleton
import src.core.config as cfg


class Entity:
    """
    Represents a generic entity with a name, creation time, and optional destruction time.
    """

    def __new__(cls, *args, **kwargs):
        entity_type = kwargs.get("entity_type", "Default")
        pool = EntityManager.reycled_entities.get(entity_type, [])

        for i, instance in enumerate(pool):
            if type(instance) is cls:
                return pool.pop(i)

        return super().__new__(cls)

    def __init__(self, name: str,
                 creation_time: Union[int, float],
                 entity_type: str = "Default",
                 is_parent: bool = False,
                 is_vehicle_routed: bool = False,
                 sequence_index=None) -> None:

        """
        Initializes an Entity instance and adds it to the EntityManager class for tracking.

        :param name (str): The name of the entity.
        :param creation_time (Union[int, float]): The creation time of the entity.
        :param entity_type (str): The type of the entity.
        :param attributes (Dict[str, Any]): Additional attributes for the entity.
        """
        self.name = name
        self.creation_time = creation_time
        self.destruction_time: Optional[Union[int, float]] = None
        self.entity_type = entity_type

        if entity_type != "Default":
            gi.COLLECT_ENTITY_TYPE_STATS = True

        self.is_parent = is_parent
        self.is_vehicle_routed = is_vehicle_routed
        self.batch_members = []

        self.current_location = None
        self.destination = None

        if sequence_index is not None:
            self.sequence_index = sequence_index

        EntityManager.add_entity(self)

    def __repr__(self) -> str:
        """
        Provides a string representation of the Entity instance, showing its lifecycle.

        :return: str: A string representation of the entity, including its name, creation time,
        and destruction time (if any).
        """
        return f"{self.name} ({self.creation_time})" if not self.destruction_time \
            else f"{self.name} ({self.destruction_time - self.creation_time})"

    def reset(self) -> None:
        pass


class EntityManager(Singleton):
    """
     Manages a collection of Entity instances. Utilizes the Singleton design pattern to ensure that only one instance of
     this class exists throughout the application.
     This class is responsible for adding entities to a tracking list and for the destruction of all entities
     within that list.
     """
    entities: List[Entity] = []
    reycled_entities: Dict[str, List[Entity]] = defaultdict(list)
    max_pool_size_by_type: Dict[str, int] = defaultdict(lambda: 500)

    entity_type_stats: Dict[str, Dict[str, float]] = {}
    entity_types_list: List[str] = []
    entity_type_total_time: Dict[str, float] = defaultdict(float)

    entity_type_weighted_sum: Dict[str, float] = {}
    entity_type_last_change_time: Dict[str, float] = {}
    entity_type_count: Dict[str, int] = {}

    current_number_in_system: int = 0
    last_change_time: float = 0.0
    time_weighted_sum: float = 0.0
    number_created: int = 0
    number_destroyed: int = 0
    max_time_in_system: float = 0.0
    min_time_in_system: float = float('inf')
    total_time_in_system: float = 0.0

    @classmethod
    def initialize(cls, env: Environment) -> None:
        """
        Initialize EntityManager with the simulation environment.
        :param env: The simulation environment.
        """
        cls.env = env

        # Initialize max pool sizes from settings
        cls.max_pool_size_by_type = defaultdict(lambda: cfg.entity_pool_default)

        cls.current_number_in_system = 0
        cls.last_change_time = env.now
        cls.time_weighted_sum = 0.0
        cls.number_created = 0
        cls.number_destroyed = 0
        cls.max_time_in_system = 0.0
        cls.min_time_in_system = float('inf')
        cls.total_time_in_system = 0.0
        cls.entity_type_stats.clear()

    @classmethod
    def add_entity(cls, entity: Entity) -> None:
        """
        Adds an Entity instance to the EntityManager's list for tracking. This method ensures that all entities
        are accounted for and can be managed collectively.

        :param entity: The Entity instance to be added to the tracking list.
        """
        cls._update_time_weighted_sum()
        cls.entities.append(entity)
        cls.current_number_in_system += 1
        if entity.creation_time >= gi.DURATION_WARM_UP:
            cls.number_created += 1

        cls.initialize_entity_types(entity)

        # Make sure the pool exists
        if entity.entity_type not in cls.reycled_entities:
            cls.reycled_entities[entity.entity_type] = []

    @classmethod
    def remove_entity(cls, entity: Entity) -> None:
        """
        Removes an Entity instance from the EntityManager.
        """
        time_in_system = entity.destruction_time - entity.creation_time

        # Update statistics only for entities created AND destroyed after warm-up
        if entity.destruction_time is not None:
            counts_for_stats = (entity.creation_time >= gi.DURATION_WARM_UP and
                                entity.destruction_time > gi.DURATION_WARM_UP)

            if counts_for_stats:
                cls.total_time_in_system += time_in_system
                cls.max_time_in_system = max(cls.max_time_in_system, time_in_system)
                cls.min_time_in_system = min(cls.min_time_in_system, time_in_system)
                cls.number_destroyed += 1

        cls._update_time_weighted_sum()

        if entity in cls.entities:
            cls.entities.remove(entity)
            cls.current_number_in_system -= 1
            cls.update_entity_type_stats(entity, time_in_system)

        # Recycle by type
        pool = cls.reycled_entities.setdefault(entity.entity_type, [])
        max_pool_size = cfg.get_entity_pool_size(entity.entity_type)

        if len(pool) < max_pool_size:
            entity.reset()
            pool.append(entity)
        else:
            del entity

    @classmethod
    def _update_time_weighted_sum(cls) -> None:
        """
        Updates the time-weighted sum based on the current simulation time.
        """
        now = cls.env.now

        if now <= gi.DURATION_WARM_UP:
            cls.last_change_time = max(cls.last_change_time, now)
            return

        # Handle case where we're crossing the warm-up boundary
        if cls.last_change_time < gi.DURATION_WARM_UP:
            duration = now - gi.DURATION_WARM_UP
            cls.time_weighted_sum += cls.current_number_in_system * duration
            cls.last_change_time = now
            return

        duration = now - cls.last_change_time
        cls.time_weighted_sum += cls.current_number_in_system * duration
        cls.last_change_time = now

    @classmethod
    def finalize_statistics(cls) -> float:
        """
        Finalize the time-weighted average for NumberInSystem.
        :return: Time-weighted average of NumberInSystem.
        """

        cls._update_time_weighted_sum()
        total_time = cls.env.now
        effective_time = total_time - gi.DURATION_WARM_UP if gi.DURATION_WARM_UP > 0 else total_time

        if effective_time <= 0:
            return 0

        return cls.time_weighted_sum / effective_time

    @classmethod
    def avg_time(cls) -> float:
        """
        Calculate the avg_time_in_system and return the result.
        """
        avg_time_in_system = cls.total_time_in_system / cls.number_destroyed if cls.number_destroyed > 0 else 0
        return avg_time_in_system

    @classmethod
    def destroy_all_entities(cls) -> None:
        """
        Reset the EntityManager state while properly capturing statistics.
        This method ensures the NumberInSystem statistic is calculated before resetting.
        """
        # Update the time-weighted sum to ensure correct NumberInSystem calculation
        cls._update_time_weighted_sum()

        # Clear entity collections
        cls.entities.clear()
        cls.reycled_entities.clear()
        cls.max_pool_size_by_type.clear()

        # Reset counters and tracking variables
        cls.current_number_in_system = 0
        cls.last_change_time = cls.env.now if hasattr(cls, 'env') else 0
        cls.time_weighted_sum = 0.0
        cls.number_created = 0
        cls.number_destroyed = 0
        cls.max_time_in_system = 0.0
        cls.min_time_in_system = float('inf')
        cls.total_time_in_system = 0.0

        cls.entity_type_weighted_sum.clear()
        cls.entity_type_last_change_time.clear()
        cls.entity_type_weighted_sum.clear()
        cls.entity_type_last_change_time.clear()
        cls.entity_type_count.clear()

    @classmethod
    def initialize_entity_types(cls, entity: Entity):
        # Before incrementing
        cls._update_type_weighted_sum(entity.entity_type)
        # Now increment
        cls.entity_type_count[entity.entity_type] = cls.entity_type_count.get(entity.entity_type, 0) + 1

        # If the entity_type is new, append to list
        if entity.entity_type not in cls.entity_types_list:
            cls.entity_types_list.append(entity.entity_type)

        # Initialize dictionary with enitity-statistics for every entity_type
        if entity.entity_type not in cls.entity_type_stats:
            cls.entity_type_stats[entity.entity_type] = {
                "NumberInSystem (average)": 0.0,
                "NumberCreated": 0,
                "NumberDestroyed": 0,
                "NumberRemaining": 0,
                "TimeInSystem (average)": 0.0,
                "TimeInSystem (max)": 0.0,
                "TimeInSystem (min)": float('inf'),
                "TotalTimeInSystem": 0.0
            }

        cls.entity_type_stats[entity.entity_type]["NumberCreated"] += 1

    @classmethod
    def update_entity_type_stats(cls, entity: Entity, time_in_system):

        cls._update_type_weighted_sum(entity.entity_type)

        if entity.entity_type in cls.entity_type_count:
            cls.entity_type_count[entity.entity_type] -= 1

        cls.entity_type_total_time[entity.entity_type] += time_in_system

        stats = cls.entity_type_stats[entity.entity_type]
        stats["NumberInSystem (average)"] = EntityManager.avg_number_per_type()
        stats["NumberDestroyed"] += 1
        stats["TotalTimeInSystem"] += time_in_system
        stats["TimeInSystem (average)"] = stats["TotalTimeInSystem"] / stats["NumberDestroyed"]
        stats["TimeInSystem (max)"] = max(stats["TimeInSystem (max)"], time_in_system)
        stats["TimeInSystem (min)"] = min(stats["TimeInSystem (min)"], time_in_system)
        stats["NumberRemaining"] = stats["NumberCreated"] - stats["NumberDestroyed"]

    @classmethod
    def _update_type_weighted_sum(cls, entity_type: str) -> None:
        now = cls.env.now
        last_time = cls.entity_type_last_change_time.get(entity_type, now)
        duration = now - last_time
        count = cls.entity_type_count.get(entity_type, 0)

        # Add time-weighted contribution
        cls.entity_type_weighted_sum[entity_type] = cls.entity_type_weighted_sum.get(entity_type, 0.0) + (count * duration)
        cls.entity_type_last_change_time[entity_type] = now

    @classmethod
    def avg_number_per_type(cls):
        now = cls.env.now

        for entity_type in cls.entity_types_list:
            cls._update_type_weighted_sum(entity_type)
            weighted = cls.entity_type_weighted_sum.get(entity_type, 0.0)
            number_in_system = weighted / now if now > 0 else 0.0

            return number_in_system

        return None
