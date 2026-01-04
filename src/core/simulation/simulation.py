from typing import Union, Dict, Any
from src.core.simulation.runner import SimulationRunner
from src.core.simulation.replication import ReplicationRunner
import src.core.config as cfg


def run_simulation(model, steps, warm_up=None, store_pivot_in_file=None, new_database=True,
                   config: Union[str, Dict[str, Any], None] = None, show_progress: bool = False,
                   skip_statistics: bool = False):
    """
    Run a single simulation using the specified model.

    :param model: The simulation model function.
    :param steps: Number of steps (or minutes) to run the simulation.
    :param warm_up: Warm-up duration to ignore in the statistics.
    :param store_pivot_in_file: Optional file path to store the pivot table as CSV.
    :param new_database: Whether to create a new database table.
    :param config: Configuration overrides. Can be:
                   - None: use global config
                   - str: path to YAML config file
                   - dict: inline configuration overrides
    :param show_progress: Whether to display a progress bar during simulation.
    :param skip_statistics: Whether to skip framework statistics collection (faster for custom stats).
    :return: The pivot table summarizing simulation statistics (or None if skip_statistics=True).
    """
    # Apply configuration overrides before running simulation
    cfg.apply_overrides(config)

    try:
        runner = SimulationRunner(model, steps, warm_up, show_progress=show_progress,
                                  skip_statistics=skip_statistics)
        return runner.run(store_pivot_in_file, new_database)
    finally:
        # Reset to global configuration after simulation
        cfg.reset_to_global()


def run_replications(model, steps, num_replications, warm_up=None,
                     multiprocessing=False, store_pivot_in_file=None,
                     new_database=True, confidence=0.95,
                     enable_detailed_replication_data=True,
                     config: Union[str, Dict[str, Any], None] = None,
                     show_progress: bool = False, skip_statistics: bool = False):
    """
    Run multiple replications of the simulation.

    :param model: The simulation model function.
    :param steps: Number of steps (or minutes) per replication.
    :param num_replications: Total number of replications.
    :param warm_up: Warm-up duration to ignore in the statistics.
    :param multiprocessing: Whether to use multiprocessing.
    :param store_pivot_in_file: Optional file path to store the pivot table as CSV.
    :param new_database: Whether to create a new database table.
    :param confidence: Confidence level for statistical calculations (default: 0.95).
    :param enable_detailed_replication_data: Whether to store detailed data from each replication (default: True).
                                           Set to False to save memory when detailed data is not needed.
    :param config: Configuration overrides. Can be:
                   - None: use global config
                   - str: path to YAML config file
                   - dict: inline configuration overrides
    :param show_progress: Whether to display a progress bar during each replication.
    :param skip_statistics: Whether to skip framework statistics collection (faster for custom stats).
    :return: The aggregated pivot table summarizing replication statistics (or None if skip_statistics=True).
    """
    # Apply configuration overrides before running replications
    cfg.apply_overrides(config)

    try:
        rep_runner = ReplicationRunner(
            model, steps, num_replications, warm_up, multiprocessing,
            confidence, enable_detailed_replication_data,
            config_overrides=config, show_progress=show_progress,
            skip_statistics=skip_statistics
        )
        return rep_runner.run(store_pivot_in_file, new_database)
    finally:
        # Reset to global configuration after replications
        cfg.reset_to_global()
