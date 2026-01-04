from abc import ABC, abstractmethod

import simpy

from src.core.types.componet_type import ComponentType


class ResetAbleNamedObjectManager:
    """
    Manages a collection of resettable named objects.

    Attributes:
        resetable_named_objects (list): List of resettable named objects.
    """

    def __init__(self):
        """
        Initialize the manager with an empty list of resettable named objects.
        """
        self.resetable_named_objects = []
        self._object_names = set()
        self._object_pool = {}

    def add(self, rno):
        """
        Add a resettable named object to the manager.

        :param rno: The resettable named object to add.
        """
        # Check if an object with this name already exists in the active list
        for i, obj in enumerate(self.resetable_named_objects):
            if obj.name == rno.name and obj is not rno:
                # Replace the old object with the new one
                self.resetable_named_objects[i] = rno
                self._object_pool[rno.name] = rno
                return

        self.resetable_named_objects.append(rno)
        self._object_pool[rno.name] = rno

    def __iter__(self):
        """
        Initialize the iteration object for the manager.

        :return: The manager itself as an iterator.
        """
        self.iteration_object = -1
        return self

    def __next__(self):
        """
        Get the next resettable named object in the iteration.

        :return: The next resettable named object.
        :raises StopIteration: If there are no more objects to iterate over.
        """
        self.iteration_object += 1
        if self.iteration_object < len(self.resetable_named_objects):
            return self.resetable_named_objects[self.iteration_object]
        raise StopIteration

    def reset_all(self):
        """
        Reset all resettable named objects managed by this manager and clear the list.
        """
        for rno in self.resetable_named_objects:
            rno.reset()

        self.resetable_named_objects = []
        self._object_names = set()
        self._object_pool.clear()

    def __repr__(self) -> str:
        """
        Provide a string representation of the manager and its managed objects.

        :return: A string representation of the manager.
        """
        object_details = ", ".join(repr(obj) for obj in self.resetable_named_objects)
        return f'ResetAbleNamedObjects({len(self.resetable_named_objects)} objects: {object_details})'

    def __len__(self) -> int:
        return len(self.resetable_named_objects)


class ResetAbleNamedObject(ABC):
    """
    Abstract base class for resettable named objects.

    Attributes:
        name (str): The name of the object.
        env (simpy.Environment): The SimPy environment in which the object operates.
    """

    def __init__(self, env: simpy.Environment, name: str, componet_type: ComponentType, rnom: ResetAbleNamedObjectManager):
        """
        Initialize a resettable named object with a name and environment, and add it to a manager.

        :param env: SimPy environment.
        :param name: Name of the object.
        :param rnom: Manager to which this object will be added.
        """
        self.name = name
        self.env = env
        rnom.add(self)

        """
        Sink Stats
        """
        if componet_type == ComponentType.SINKS:
            self.total_time_in_system = 0
            self.max_time_in_system_pivot_table = 0
            self.min_time_in_system_pivot_table = float('inf')
            self.number_entered_pivot_table = 0
            self.entities_processed = 0
            self.units_utilized_over_time = []

        """
        Server Stats
        """
        if componet_type == ComponentType.SERVERS:
            self.start_processing_time = 0
            self.total_entities_processed_pivot_table = 0
            self.total_processing_time_pivot_table = 0
            self.number_entered_pivot_table = 0
            self.number_exited_pivot_table = 0
            self.units_allocated_pivot_table = 0
            self.units_utilized_pivot_table = 0
            self.total_downtime_pivot_table = 0
            self.number_downtimes_pivot_table = 0
            self.uptime_pivot_table = 0
            self.total_uptime_pivot_table = 0
            self.number_uptimes_pivot_table = 0
            self.units_utilized_over_time = []

        """
        Combiner Stats
        """
        if componet_type == ComponentType.COMBINER:
            self.start_processing_time = 0
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

        """
        Source Stats
        """
        if componet_type == ComponentType.SOURCES:
            self.entities_created_pivot_table = 0
            self.number_exited_pivot_table = 0

        """
        Seperator Stats
        """
        if componet_type == ComponentType.SEPARATORS:
            self.start_processing_time = 0
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

        """
        Vehicle Stats
        """
        if componet_type == ComponentType.VEHICLES:
            self.total_trips = 0
            self.total_travel_time = 0
            self.entities_transported = 0
            self.utilized_time = 0
            self.time_utilized_over_time = []
            self.queue_lengths = []
            self.queue_times = []
            self.current_queue_length = 0

        """
        Storage Stats
        """
        if componet_type == ComponentType.STORAGE:
            self.start_processing_time = 0
            self.total_entities_processed_pivot_table = 0
            self.total_processing_time_pivot_table = 0
            self.number_entered_pivot_table = 0
            self.number_exited_pivot_table = 0
            self.units_allocated_pivot_table = 0
            self.units_utilized_pivot_table = 0
            self.total_downtime_pivot_table = 0
            self.number_downtimes_pivot_table = 0
            self.uptime_pivot_table = 0
            self.total_uptime_pivot_table = 0
            self.number_uptimes_pivot_table = 0
            self.units_utilized_over_time = []

    @abstractmethod
    def reset(self):
        """
        Reset the state of the object. This method must be implemented by subclasses.
        """
        pass

    def __repr__(self) -> str:
        return self.name
