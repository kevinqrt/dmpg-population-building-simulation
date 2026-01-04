import pandas as pd

import src.core.global_imports as gi
import src.core.config as cfg
from src.core.statistics.entity_type_stats import collect_all_entity_type_stats
from src.core.statistics.stats import calculate_statistics
from src.core.utils.helper import round_value
from src.core.components.worker_pool import print_worker_utilization_for_pool, print_all_worker_pools_summary
from src.core.components.model import Model

from database.base.models import run_simulation_table, db
from database.base.database_config import drop_table, initialize_table
from database.simulation.simulation_db import store_run_simulation, create_pivot_run_simulation
from database.simulation.simulation_entity_types_db import store_entity_type_stats, create_etype_pivot, create_etype_table


class SimulationRunner:
    """
    Runs a single simulation using the provided model function.
    """

    def __init__(self, model, steps, warm_up=None, show_progress=False, skip_statistics=False):
        """
        :param model: Callable simulation model function.
        :param steps: Number of steps (or minutes) to run the simulation.
        :param warm_up: Warm-up duration to ignore in the statistics.
        :param show_progress: Whether to display a progress bar during simulation.
        :param skip_statistics: Whether to skip framework statistics collection.
        """
        self.model = model
        self.steps = steps
        self.warm_up = warm_up
        self.show_progress = show_progress
        self.skip_statistics = skip_statistics

    def run(self, store_pivot_in_file: str = None, new_database: bool = True) -> pd.DataFrame:
        """
        Execute the simulation and return a pivot table summarizing the stats.
        """
        # Sync config values to global variables
        gi.set_collect_entity_type_stats(cfg.collect_entity_type_stats)
        if self.warm_up is not None:
            gi.set_duration_warm_up(self.warm_up)
        else:
            gi.set_duration_warm_up(cfg.duration_warm_up)

        # Set random seed for test reproducibility
        gi.set_random_seed(cfg.random_seed)

        # 1. Run the simulation through Model
        env = Model().run_simulation(
            model_func=self.model,
            duration=self.steps,
            seed=cfg.random_seed,
            warm_up=gi.DURATION_WARM_UP,
            show_progress=self.show_progress
        )

        # Skip statistics collection if requested (faster for custom stats)
        if self.skip_statistics:
            return None

        # 2. Collect and format statistics
        stats = calculate_statistics(env)
        data = self._format_stats(stats)

        # 3. Store results in database/file
        if new_database:
            drop_table(run_simulation_table)
            initialize_table(run_simulation_table)

        with db.atomic():
            store_run_simulation(data)

        # 3.1 if Entity Type Stats
        if cfg.collect_entity_type_stats:
            entity_type_data = collect_all_entity_type_stats(env)

            with db.atomic():
                store_entity_type_stats(entity_type_data)

            pivot_enitity_types = create_etype_pivot()
            create_etype_table(pivot_enitity_types)

            if store_pivot_in_file:
                pivot_enitity_types.to_csv(store_pivot_in_file)

            return pivot_enitity_types

        # 3.2 print table
        pivot_table = create_pivot_run_simulation()

        if store_pivot_in_file:
            pivot_table.to_csv(store_pivot_in_file)

        if Model().worker_pools:
            print_all_worker_pools_summary(env.now)

            for pool_name, pool in Model().worker_pools.items():
                print_worker_utilization_for_pool(pool_name, env.now)

        return pivot_table

    def _format_stats(self, stats: tuple) -> list:
        """
        Convert statistics into a list of dictionaries.
        """
        (entity_stats, server_stats, sink_stats, source_stats, vehicle_stats, storage_stats, separator_stats, combiner_stats) = stats
        data = []

        # Entity Stats
        for key, value in entity_stats.items():
            data.append({'Type': 'Entity', 'Name': 'Entity', 'Stat': key, 'Value': round_value(value)})

        # Server Stats
        for stat in server_stats:
            for key, value in stat.items():
                if key != 'Server':
                    data.append({'Type': 'Server', 'Name': stat['Server'], 'Stat': key, 'Value': round_value(value)})

        # Sink Stats
        for sink_name, stat_dict in sink_stats.items():
            for key, value in stat_dict.items():
                data.append({'Type': 'Sink', 'Name': sink_name, 'Stat': key, 'Value': round_value(value)})

        # Source Stats
        for source_name, stat_dict in source_stats.items():
            for key, value in stat_dict.items():
                data.append({'Type': 'Source', 'Name': source_name, 'Stat': key, 'Value': round_value(value)})

        # Vehicle Stats
        for stat in vehicle_stats:
            for key, value in stat.items():
                if key != 'Vehicle':
                    data.append({'Type': 'Vehicle', 'Name': stat['Vehicle'], 'Stat': key, 'Value': round_value(value)})

        # Storage Stats
        for stat in storage_stats:
            for key, value in stat.items():
                if key != 'Storage':
                    data.append({'Type': 'Storage', 'Name': stat['Storage'], 'Stat': key, 'Value': round_value(value)})

        # Separator Stats
        for stat in separator_stats:
            for key, value in stat.items():
                if key != 'Separator':
                    data.append({'Type': 'Separator', 'Name': stat['Separator'], 'Stat': key, 'Value': round_value(value)})

            # Combiner Stats
        for stat in combiner_stats:
            for key, value in stat.items():
                if key != 'Combiner':
                    data.append({'Type': 'Combiner', 'Name': stat['Combiner'], 'Stat': key, 'Value': round_value(value)})

        # Global Tally Statistics
        for stat_name, (min_, max_, avg) in Model().get_all_tally_statistics().items():
            data.append({'Type': 'Tally', 'Name': stat_name, 'Stat': 'Min', 'Value': round_value(min_)})
            data.append({'Type': 'Tally', 'Name': stat_name, 'Stat': 'Max', 'Value': round_value(max_)})
            data.append({'Type': 'Tally', 'Name': stat_name, 'Stat': 'Average', 'Value': round_value(avg)})

        return data
