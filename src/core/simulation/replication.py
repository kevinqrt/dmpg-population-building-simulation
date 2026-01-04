import time
import pandas as pd
import concurrent.futures
from typing import Dict
import numpy as np
from scipy.stats import norm, t
import src.core.global_imports as gi
import src.core.config as cfg

from src.core.components.model import Model
from src.core.global_imports import Stats
from src.core.statistics.stats import calculate_statistics, calculate_all_stats
from src.core.utils.utils import print_stats
from src.core.statistics.entity_type_stats import collect_all_entity_type_stats

from database.base.models import run_replications_table
from database.base.database_config import drop_table, initialize_table
from database.replication.replication_db import store_run_replication, create_pivot_run_replication
from database.replication.replication_entity_types_db import create_table_entity_types_replication


class ReplicationRunner:
    """
    Runs multiple simulation replications and aggregates statistics.
    """

    def __init__(self, model, steps, num_replications, warm_up=None, multiprocessing=False, confidence=0.95,
                 enable_detailed_replication_data=True, config_overrides=None, show_progress=False,
                 skip_statistics=False):
        """
        :param model: Callable simulation model function.
        :param steps: Run duration per replication.
        :param num_replications: Total replications.
        :param warm_up: Warm-up duration.
        :param multiprocessing: Enable parallel execution.
        :param confidence: Confidence level for statistical calculations (default: 0.95).
        :param enable_detailed_replication_data: Whether to store detailed data from each replication (default: True).
                                                 Set to False to save memory when detailed data is not needed.
        :param config_overrides: Config to apply in each subprocess.
        :param show_progress: Whether to display a progress bar during each replication.
        :param skip_statistics: Whether to skip framework statistics collection (faster for custom stats).
        """
        self.model = model
        self.steps = steps
        self.num_replications = num_replications
        self.warm_up = warm_up
        self.multiprocessing = multiprocessing
        self.confidence = confidence
        self.enable_detailed_replication_data = enable_detailed_replication_data
        self.config_overrides = config_overrides
        self.show_progress = show_progress
        self.skip_statistics = skip_statistics
        self.all_entity_stats = []
        self.all_server_stats = {}
        self.all_sink_stats = {}
        self.all_source_stats = {}
        self.all_vehicle_stats = {}
        self.all_storage_stats = {}
        self.all_separator_stats = {}
        self.all_combiner_stats = {}
        self.start_time = time.time()

        self.all_entity_type_stats_df = pd.DataFrame()
        self.all_tally_stats: Dict[str, Dict[str, list[float]]] = {}

        # Only initialize detailed_replication_data if enabled
        self.detailed_replication_data = [] if enable_detailed_replication_data else None

    def run(self, store_pivot_in_file: str = None, new_database: bool = True):
        """
        Execute all replications and return the aggregated pivot table.
        """
        # Sync config values to global variables
        gi.set_collect_entity_type_stats(cfg.collect_entity_type_stats)

        # Set random seed for test reproducibility
        gi.set_random_seed(cfg.random_seed)

        Stats.all_detailed_stats = []

        # Only reset detailed data if it's enabled
        if self.enable_detailed_replication_data:
            self.detailed_replication_data = []

        tenth_percentage = int(self.num_replications / 10) or 1

        if self.multiprocessing:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = [
                    executor.submit(self._run_single_replication, r)
                    for r in range(self.num_replications)
                ]
                for r, future in enumerate(concurrent.futures.as_completed(futures)):
                    if not self.skip_statistics:
                        entity_stats, server_stats, sink_stats, source_stats, vehicle_stats, storage_stats, separator_stats, combiner_stats, entity_type_data, tally_stats = future.result()
                        self._process_results(entity_stats, server_stats, sink_stats, source_stats, vehicle_stats, storage_stats, combiner_stats, separator_stats, entity_type_data, tally_stats)
                    print_stats(r, self.num_replications, self.start_time, tenth_percentage)
        else:
            for r in range(self.num_replications):
                results = self._run_single_replication(r)
                if not self.skip_statistics:
                    (entity_stats, server_stats, sink_stats, source_stats,
                     vehicle_stats, storage_stats, separator_stats, combiner_stats, entity_type_data, tally_stats) = results
                    self._process_results(
                        entity_stats, server_stats, sink_stats, source_stats,
                        vehicle_stats, storage_stats, separator_stats, combiner_stats,
                        entity_type_data=entity_type_data,
                        tally_stats=tally_stats
                    )
                print_stats(r, self.num_replications, self.start_time, tenth_percentage)

        # Skip statistics aggregation if requested
        if self.skip_statistics:
            return None

        combined_stats = calculate_all_stats(
            self.all_entity_stats, self.all_server_stats, self.all_sink_stats,
            self.all_source_stats, self.all_vehicle_stats, self.all_storage_stats,
            self.all_separator_stats, self.all_combiner_stats,
            ['NumberCreated', 'NumberDestroyed', 'NumberInSystem (average)', 'NumberRemaining', 'TimeInSystem (average)', 'TimeInSystem (max)', 'TimeInSystem (min)'],
            ['EntitiesInQueue (average)', 'EntitiesInQueue (max)', 'EntitiesInQueue (total)', 'EntitiesProcessed', 'NumberDowntimes',
             'ScheduledUtilization', 'StarvingTime (scheduled)', 'StarvingTime (total)', 'TimeInQueue (average)', 'TimeInQueue (max)',
             'TimeProcessing (average)', 'TimeProcessing (total)', 'TotalDowntime', 'UnitsUtilized'],
            ['NumTimesProcessed (average)', 'NumTimesProcessed (max)', 'NumTimesProcessed (min)', 'NumberEntered', 'TimeInSystem (average)', 'TimeInSystem (max)', 'TimeInSystem (min)'],
            ['NumberCreated', 'NumberExited'],
            ['EntitiesInQueue (average)', 'EntitiesInQueue (max)', 'EntitiesInQueue (total)', 'EntitiesTransported', 'NumberDowntimes', 'ScheduledUtilization', 'StarvingTime (scheduled)', 'StarvingTime (total)',
             'TimeInQueue (average)', 'TimeInQueue (max)', 'TotalDowntimes', 'TotalTrips', 'TravelTime (average)', 'TravelTime (total)', 'UnitsUtilized'],
            ['EntitiesInQueue (average)', 'EntitiesInQueue (max)', 'EntitiesInQueue (total)', 'EntitiesProcessed',
             'ScheduledUtilization', 'StarvingTime (scheduled)', 'StarvingTime (total)', 'TimeInQueue (average)', 'TimeInQueue (max)', 'TimeProcessing (average)', 'TimeProcessing (total)', 'UnitsUtilized'],
            ['EntitiesInQueue (average)', 'EntitiesInQueue (max)', 'EntitiesInQueue (total)', 'EntitiesProcessed', 'NumberDowntimes',
             'ScheduledUtilization', 'StarvingTime (scheduled)', 'StarvingTime (total)', 'TimeInQueue (average)', 'TimeInQueue (max)',
             'TimeProcessing (average)', 'TimeProcessing (total)', 'TotalDowntime', 'UnitsUtilized'],
            ['EntitiesInQueue (total)', 'EntitiesProcessed', 'NumberDowntimes', 'MembersEntered', 'MembersInQueue (average)', 'MembersInQueue (max)',
             'Members TimeInQueue (average)', 'Members TimeInQueue (max)', 'ParentsEntered', 'ParentsInQueue (average)', 'ParentsInQueue (max)', 'Parents TimeInQueue (average)',
             'Parents TimeInQueue (max)', 'ScheduledUtilization', 'StarvingTime (scheduled)', 'StarvingTime (total)', 'TimeProcessing (average)', 'TimeProcessing (total)',
             'TotalDowntime', 'UnitsUtilized'],
            self.confidence
        )

        # add tally_stats
        combined_stats.extend(self.aggregate_tally_stats())

        if new_database:
            drop_table(run_replications_table)
            initialize_table(run_replications_table)

        store_run_replication(combined_stats)

        if gi.COLLECT_ENTITY_TYPE_STATS:
            entity_type_table = create_table_entity_types_replication(etype_df=self.all_entity_type_stats_df)
            gi.set_collect_entity_type_stats(False)
            return entity_type_table

        combined_pivot_table = create_pivot_run_replication()

        if store_pivot_in_file:
            combined_pivot_table.to_csv(store_pivot_in_file)

        return combined_pivot_table

    def _run_single_replication(self, replication_number):
        """
        Run a single replication and return statistics.
        """
        if self.config_overrides is not None:
            cfg.apply_overrides(self.config_overrides)

        env = Model().run_simulation(
            model_func=self.model,
            duration=self.steps,
            seed=replication_number,
            warm_up=self.warm_up,
            show_progress=self.show_progress
        )

        # Skip statistics collection if requested
        if self.skip_statistics:
            return None, [], {}, {}, [], [], [], [], None, {}

        # collect tally_stats for every run
        tally_stats = {}
        for name, tally in Model().get_tally_statistics().items():
            min_, max_, avg = tally.calculate_statistics()
            tally_stats[name] = {"min": min_, "max": max_, "avg": avg}

        entity_type_data = collect_all_entity_type_stats(env) if gi.COLLECT_ENTITY_TYPE_STATS else None

        return *calculate_statistics(env), entity_type_data, tally_stats

    def _process_results(self, entity_stats, server_stats, sink_stats, source_stats, vehicle_stats, storage_stats, separator_stats,
                         combiner_stats, entity_type_data=None, tally_stats=None):
        """
        Update the overall accumulators with a replication's results.
        """
        # Create replication data dictionary
        replication_data = {
            'Entity': entity_stats,
            'Server': server_stats,
            'Sink': sink_stats,
            'Source': source_stats,
            'Vehicle': vehicle_stats,
            'Storage': storage_stats,
            'Separator': separator_stats,
            'Combiner': combiner_stats
        }

        # Only save detailed replication data if enabled
        if self.enable_detailed_replication_data:
            self.detailed_replication_data.append(replication_data)

        # Process overall statistics (always needed for aggregation)
        self.all_entity_stats.append(entity_stats)
        for stat in server_stats:
            server_name = stat['Server']
            self.all_server_stats.setdefault(server_name, []).append(stat)
        for sink_name, stat in sink_stats.items():
            self.all_sink_stats.setdefault(sink_name, []).append(stat)
        for source_name, stat in source_stats.items():
            self.all_source_stats.setdefault(source_name, []).append(stat)
        for stat in vehicle_stats:
            vehicle_name = stat['Vehicle']
            self.all_vehicle_stats.setdefault(vehicle_name, []).append(stat)
        for stat in storage_stats:
            storage_name = stat['Storage']
            self.all_storage_stats.setdefault(storage_name, []).append(stat)
        for stat in separator_stats:
            separator_name = stat['Separator']
            self.all_separator_stats.setdefault(separator_name, []).append(stat)
        for stat in combiner_stats:
            combiner_name = stat['Combiner']
            self.all_combiner_stats.setdefault(combiner_name, []).append(stat)

        Stats.all_detailed_stats.append({
            'Entity': entity_stats,
            'Server': server_stats,
            'Sink': sink_stats,
            'Source': source_stats,
            'Vehicle': vehicle_stats,
            'Storage': storage_stats,
            'Separator': separator_stats,
            'Combiner': combiner_stats
        })

        if gi.COLLECT_ENTITY_TYPE_STATS and entity_type_data:
            df = pd.DataFrame(entity_type_data)
            self.all_entity_type_stats_df = pd.concat([self.all_entity_type_stats_df, df], ignore_index=True)

        if tally_stats:
            for key, values in tally_stats.items():
                if key not in self.all_tally_stats:
                    self.all_tally_stats[key] = {"min": [], "max": [], "avg": []}
                self.all_tally_stats[key]["min"].append(values["min"])
                self.all_tally_stats[key]["max"].append(values["max"])
                self.all_tally_stats[key]["avg"].append(values["avg"])

    def aggregate_tally_stats(self):
        result = []
        for name, series in self.all_tally_stats.items():
            for metric in ["min", "max", "avg"]:
                values = series[metric]
                arr = np.array(values)
                n = len(arr)

                if n == 0:
                    continue

                min_val = float(np.min(arr))
                max_val = float(np.max(arr))
                mean_val = float(np.mean(arr))
                std = float(np.std(arr, ddof=1)) if n > 1 else 0

                # Half-width confidence interval
                if n <= 1:
                    hw = 0
                elif n > 30:
                    hw = norm.ppf((1 + self.confidence) / 2) * (std / np.sqrt(n))
                else:
                    hw = t.ppf((1 + self.confidence) / 2, df=n - 1) * (std / np.sqrt(n))

                result.append({
                    "Type": "Tally",
                    "Name": name,
                    "Stat": metric.capitalize(),
                    "Average": round(mean_val, 4),
                    "Minimum": round(min_val, 4),
                    "Maximum": round(max_val, 4),
                    "Half-Width": round(hw, 4)
                })

        return result
