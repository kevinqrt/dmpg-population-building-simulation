import re
from typing import Union

import pandas as pd
import simpy

from src.core.components.entity import EntityManager
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components_abstract.resetable_named_object import ResetAbleNamedObjectManager
from src.core.components_abstract.singleton import Singleton
import src.core.config as cfg
from src.core.global_imports import set_duration_warm_up
from src.core.statistics.tally_statistic import TallyStatistic
from src.core.types.componet_type import ComponentType


class Model(metaclass=Singleton):
    """
    Singleton class that represents the simulation model, managing different types of components
    and providing methods for simulation execution.
    """
    def __init__(self):
        """
        Initialize the Model instance with dictionaries to hold different component types.
        """
        self.components = {
            ComponentType.SOURCES: ResetAbleNamedObjectManager(),
            ComponentType.SERVERS: ResetAbleNamedObjectManager(),
            ComponentType.SINKS: ResetAbleNamedObjectManager(),
            ComponentType.VEHICLES: ResetAbleNamedObjectManager(),
            ComponentType.COMBINER: ResetAbleNamedObjectManager(),
            ComponentType.SEPARATORS: ResetAbleNamedObjectManager(),
            ComponentType.STORAGE: ResetAbleNamedObjectManager()
        }

        self.routing_table = None
        self.routing_table_destination_column = None
        self.all_components = {}
        self.connection_registry = {}  # Track all connections by key
        self.state_variables = {}
        self.tally_statistics = {}
        self.routing_group = {}
        self.routing_group_strategy = {}
        self.worker_pools = {}
        self.env = None

    def register_connection(self, origin_name: str, destination_name: str, connection):
        """
        Register a connection in the global registry.

        :param origin_name: Name of the origin component
        :param destination_name: Name of the destination component
        :param connection: The connection object to register
        """
        key = f"{origin_name}â†’{destination_name}"
        self.connection_registry[key] = connection

    def get_connection(self, origin_name: str, destination_name: str):
        """
        Retrieve a connection from the registry.

        :param origin_name: Name of the origin component
        :param destination_name: Name of the destination component
        :return: Connection object or None if not found
        """
        key = f"{origin_name}â†’{destination_name}"
        return self.connection_registry.get(key)

    def run_simulation(self, model_func, duration, seed=None, warm_up=None, show_progress=False):
        """
        Run a complete simulation with proper lifecycle management.
        This is THE central method for running simulations.

        :param model_func: Function that builds the model
        :param duration: Simulation duration
        :param seed: Random seed (optional)
        :param warm_up: Warm-up duration (optional)
        :param show_progress: Whether to display a progress bar during simulation
        :return: Environment after simulation
        """
        # 1. Handle random seed
        import src.core.global_imports as gi
        gi.set_random_seed(cfg.random_seed)

        if seed is not None:
            gi.set_random_seed(seed)

        # 2. Validate and set warm-up
        if warm_up is not None and warm_up > 0:
            if warm_up >= duration:
                raise ValueError(f"Warm-up duration ({warm_up}) cannot exceed simulation length ({duration}).")
            set_duration_warm_up(warm_up)
        else:
            set_duration_warm_up(0)

        # 3. Create fresh environment
        env = simpy.Environment()

        # 4. Initialize managers with new environment
        EntityManager.initialize(env)
        if hasattr(StorageManager, 'env'):
            StorageManager.env = env

        # 5. Reset all component collections
        self.reset_simulation()

        # 6. Set model's environment reference
        self.env = env

        # 7. Build the model
        model_func(env)

        # 8. Run the simulation (with optional progress bar)
        if show_progress:
            self._run_with_progress(env, duration)
        else:
            env.run(until=duration)

        return env

    def _run_with_progress(self, env, duration):
        """
        Run simulation with a progress bar.

        :param env: SimPy environment
        :param duration: Total simulation duration
        """
        import sys

        try:
            from tqdm import tqdm
            use_tqdm = True
        except ImportError:
            use_tqdm = False

        # Calculate chunk size (update progress ~100 times, minimum 1 step)
        num_updates = 100
        chunk_size = max(1, duration // num_updates)

        if use_tqdm:
            # Use tqdm for nice progress bar (write to stderr to avoid stdout capture)
            with tqdm(total=duration, unit='steps', desc='Simulating', ncols=80, file=sys.stderr) as pbar:
                current_time = 0
                while current_time < duration:
                    next_time = min(current_time + chunk_size, duration)
                    env.run(until=next_time)
                    pbar.update(next_time - current_time)
                    current_time = next_time
        else:
            # Fallback: simple text-based progress (write to stderr)
            current_time = 0
            last_percent = -1
            while current_time < duration:
                next_time = min(current_time + chunk_size, duration)
                env.run(until=next_time)
                current_time = next_time

                percent = int(100 * current_time / duration)
                if percent != last_percent:
                    bar_width = 40
                    filled = int(bar_width * current_time / duration)
                    bar = '=' * filled + '-' * (bar_width - filled)
                    sys.stderr.write(f'\rSimulating: [{bar}] {percent}%')
                    sys.stderr.flush()
                    last_percent = percent

            sys.stderr.write('\n')
            sys.stderr.flush()

    def add_routing_group(self, group_name: str, strategy='Default') -> None:
        """
        Creates a new routing group and saves it.

        :param group_name: Unique name of the routing group.
        :param strategy: Strategy to use to get a member for routing.
        :return: None
        """

        self.routing_group[group_name] = []
        self.routing_group_strategy[group_name] = strategy

    def add_member_to_group(self, group_name: str, member_name: str) -> None:
        """
        Adds a member to the routing group.

        :param group_name: Unique name of the routing group.
        :param member_name: Unique name of the member to add.
        :return:
        """

        self.routing_group[group_name].append(member_name)

    def is_group(self, group_name: str) -> bool:
        """
        Checks if a routing group with this name exists.

        :param group_name: Group name to check.
        :return: True if exists, False otherwise.
        """

        return group_name in self.routing_group

    def get_next_destination_from_group(self, group_name: str):
        """
        Gets the next destination from group depending on the group strategy.

        :param group_name: Name of the routing group.
        :return:
        """

        member_with_smallest_queue = None

        for member_name in self.routing_group[group_name]:
            member = self.get_component_by_name(member_name)
            if self.routing_group_strategy[group_name] == 'No_Queue':
                if member.capacity > member.used_capacity:
                    return member

            # find the member with the smalles_queue
            if self.routing_group_strategy[group_name] == 'Default':
                if member_with_smallest_queue is None:
                    member_with_smallest_queue = member
                else:
                    if member.queue_length < member_with_smallest_queue.queue_length:
                        member_with_smallest_queue = member

        if member_with_smallest_queue is not None:
            return member_with_smallest_queue

    def add_state(self, state_name: str, state_value) -> None:
        """
        Adds a state variable to the model.

        :param state_name: Name of the state variable to add.
        :param state_value: Value of the state
        :return: None
        """
        self.state_variables[state_name] = state_value

    def remove_state(self, state_name: str) -> None:
        """
        Removes a state from the model

        :param state_name: Name of the state to remove.
        :return: None
        """
        del self.state_variables[state_name]

    def get_state(self, state_name: str):
        """
        Gets the value of a state.

        :param state_name: Name of the state
        :return: The value of the state
        """
        return self.state_variables[state_name]

    def update_state(self, state_name: str, value) -> None:
        """
        Updates the value of a state.

        :param state_name: Name of the state for the value update
        :param value: The value for the state
        :return: None
        """
        self.state_variables[state_name] = value

    def add_tally_statistic(self, name: str):
        """
        Adds a new tally statistic with the given name to the dictionary of tally
        statistics. The tally statistic is initialized with an empty dictionary.

        :param name: The name of the tally statistic to be added.
        :type name: str

        """
        self.tally_statistics[name] = TallyStatistic()

    def record_tally_statistic(self, name: str, value: Union[float, int, str]):
        """
        Records a statistic to the tally_statistics collection. The provided value is
        stored using the associated key (name) within the lifecycle tally system. This
        function ensures the appropriate storage and categorization of statistical data.

        :param name: The key or identifier for the statistic to record in the tally
            system.
        :type name: str
        :param value: The statistic's value to record, which can be a float, int, or str.
        :type value: Union[float, int, str]
        """
        self.tally_statistics[name].record(value)

    def calculate_tally_statistic(self, name: str):
        """
        Calculates the statistics for a specific tally based on the given name.

        This method retrieves the tally statistics associated with the provided
        name and invokes the `calculate_statistics` method to compute and return
        the resulting statistics.

        :param name: The name of the tally for which the statistics should be calculated.
        :type name: str

        :return: The computed statistics for the specified tally statistic (min, max, average).
        """
        return self.tally_statistics[name].calculate_statistics()

    def remove_tally_statistic(self, name: str):
        """
        Removes a statistic from the tally_statistics dictionary. This will delete
        the key-value pair associated with the provided name.

        :param name: The name of the tally statistic to be removed.
        :type name: str
        """
        del self.tally_statistics[name]

    def get_tally_statistics(self, name: str = None):
        """
        Retrieves tally statistics for the specified name.

        This method accesses the `tally_statistics` dictionary of the object to return
        the statistical data corresponding to the provided `name`. This can be useful
        to fetch specific metrics or recorded data for a named tally.

        :param name: The key name for which tally statistics should be retrieved.
        :type name: str
        :return: Statistics associated with the given name from the tally dictionary.
        :rtype: Any
        """
        if name is None:
            return self.tally_statistics

        return self.tally_statistics[name]

    def get_all_tally_statistics(self):
        """
        Returns all tally statistics as a dict: {stat_name: (min, max, avg)}
        """
        return {
            name: stat_obj.calculate_statistics()
            for name, stat_obj in self.tally_statistics.items()
        }

    def aggregate_statistics(self, pattern_str: str):
        # Regex pattern for matching the keys
        pattern = re.compile(pattern_str)

        min_all_values = float('inf')
        max_all_values = float('-inf')
        sum_avg = 0
        count = 0

        # Single pass through the dictionary
        for key, obj in self.tally_statistics.items():
            if pattern.match(key):
                # Get stats and update running calculations
                min_value, max_value, avg_value = obj.calculate_statistics()
                min_all_values = min(min_all_values, min_value)
                max_all_values = max(max_all_values, max_value)
                sum_avg += avg_value
                count += 1

        # Return default values if no matches found
        if count == 0:
            return {"min": 0, "max": 0, "avg": 0}

        return {
            "min": min_all_values,
            "max": max_all_values,
            "avg": sum_avg / count
        }

    def add_component(self, component, component_type: ComponentType):
        """
        Add a component to the model under the specified component type.
        Replace existing components with the same name to maintain test compatibility.

        :param component: The component to be added
        :param component_type: The type of component
        """
        # If component already exists with this name
        if component.name in self.all_components:
            if self.all_components[component.name] is component:
                return

            # Remove old component from collection to avoid duplicates
            for i, obj in enumerate(self.components[component_type].resetable_named_objects):
                if obj.name == component.name:
                    self.components[component_type].resetable_named_objects.pop(i)
                    break

        # Add the component to all_components and to the appropriate collection
        self.all_components[component.name] = component
        self.components[component_type].add(component)

    def get_components(self):
        """
        Retrieve all components in the model, organized by their type.

        :return: A dictionary with component types as keys and their respective managers as values
        """
        return {ctype.value: manager for ctype, manager in self.components.items()}

    def get_component(self, component_type: ComponentType):
        """
        Retrieve all components in the model, organized by their type.

        :return: A dictionary with component types as keys and their respective managers as values
        """

        return self.components[component_type]

    def get_component_by_name(self, name: str):
        """
        Gets component by name.

        :param name: Name of the component.

        :return: The component.
        """

        if name in self.all_components:
            return self.all_components[name]

    def add_routing_table(self, routing_table_destination_column: str, routing_table: pd.DataFrame = None,
                          routing_table_file: str = None):
        """
        Add a routing table to the model for sequence routing.

        :param routing_table_destination_column: Name of the column with the destination
        :param routing_table: A pandas dataframe represents the routing table
        :param routing_table_file: Path to a csv file for the routing table
        """
        self.routing_table_destination_column = routing_table_destination_column

        if routing_table_file:
            self.routing_table = pd.read_csv(routing_table_file)

        if routing_table is not None:
            self.routing_table = routing_table

    def reset_simulation(self):
        """
        Reset all components and prepare for a new simulation run.
        """
        # Reset all component collections
        for component_manager in self.components.values():
            component_manager.reset_all()

        # Reset entity manager
        if hasattr(EntityManager, 'env') and EntityManager.env is not None:
            EntityManager.destroy_all_entities()

        # Clear connection registry
        self.connection_registry.clear()

        # Clear all components dict
        self.all_components.clear()

        # Reset other state variables
        self.state_variables = {}
        self.routing_group = {}
        self.routing_group_strategy = {}
        self.tally_statistics = {}
        self.worker_pools = {}

        # Reset StorageManager
        from src.core.components.logistic.storage_manager import StorageManager
        StorageManager.reset()
