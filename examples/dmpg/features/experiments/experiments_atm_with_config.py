"""
ATM Experiment Model with Config File Support

Demonstrates using YAML configuration
"""

import random
import yaml
from pathlib import Path
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.experiments.experiment import ExperimentRunner
from src.core.simulation.experiments.parameter_manager import parameterize_model


@parameterize_model
def setup_atm_model(env, parameters=None):
    """
    Create the ATM banking system model.

    :param env: SimPy environment
    :param parameters: Dictionary of model parameters
    """
    params = parameters or {}

    # Get parameters with defaults
    arrival_rate = params.get('arrival_rate', 0.2)
    service_time_min = params.get('service_time_min', 3)
    service_time_max = params.get('service_time_max', 7)
    atm_capacity = params.get('ATM.capacity', 1)

    # Create model components
    source = Source(env, "CustomerArrival",
                    (lambda: random.expovariate(arrival_rate),))

    atm = Server(env, "ATM",
                 (random.uniform, service_time_min, service_time_max),
                 capacity=atm_capacity)

    exit = Sink(env, "Exit")

    # Connect components
    source.connect(atm)
    atm.connect(exit)


def load_experiment_config(config_file: str = "experiments_atm_config.yaml"):
    """
    Load experiment configuration from YAML file.

    :param config_file: Path to config file (can be relative or absolute)
    :return: Configuration dictionary
    """
    # Try multiple possible locations
    config_paths = [
        Path(config_file),  # Direct path
        Path(__file__).parent.parent.parent.parent / 'config' / config_file,  # DMPG/config/
        Path.cwd() / 'config' / config_file,  # Current working directory
    ]

    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(f"Could not find config file: {config_file}")


def run_atm_experiment_with_config(config_file: str = "experiments_atm_config.yaml"):
    """
    Run ATM experiment using scenarios defined in config file.

    :param config_file: Name or path to the experiment config file
    :return: ExperimentRunner instance with results
    """
    # Load configuration
    print(f"Loading experiment configuration from: {config_file}")
    config = load_experiment_config(config_file)

    # Extract experiment settings
    exp_config = config.get('experiment', {})
    exp_name = exp_config.get('name', 'ATM Experiment')

    # Build tracked statistics list
    tracked_stats = []
    for stat_config in config.get('tracked_statistics', []):
        stat_tuple = (
            stat_config['component_type'],
            stat_config['component_name'],
            stat_config['statistic'],
            stat_config.get('display_name')
        )
        tracked_stats.append(stat_tuple)

    # Get parameter display names
    param_display_names = config.get('parameter_display_names', {})

    # Create experiment runner
    print(f"Initializing experiment: {exp_name}")
    experiment = ExperimentRunner(
        name=exp_name,
        model_builder=setup_atm_model,
        tracked_statistics=tracked_stats,
        parameter_display_names=param_display_names
    )

    # Create scenarios from config
    scenarios_config = config.get('scenarios', [])
    print(f"Creating {len(scenarios_config)} scenarios...")

    for scenario_config in scenarios_config:
        experiment.create_scenario(
            name=scenario_config['name'],
            parameters=scenario_config['parameters'],
            description=scenario_config.get('description', '')
        )
        print(f"  ✓ {scenario_config['name']}")

    # Get simulation settings
    sim_settings = config.get('simulation_settings', {})
    steps = sim_settings.get('steps', 5000)
    replications = sim_settings.get('replications', 30)
    warm_up = sim_settings.get('warm_up', 600)
    multiprocessing = sim_settings.get('multiprocessing', True)

    # Run the experiment
    print(f"\nRunning experiment with {replications} replications per scenario...")
    print("=" * 80)

    experiment.run_all(
        steps=steps,
        replications=replications,
        warm_up=warm_up,
        multiprocessing=multiprocessing
    )

    # Display results
    print("\n" + "=" * 80)
    print("EXPERIMENT RESULTS")
    print("=" * 80)
    experiment.display_summary_table(precision=3)

    return experiment


if __name__ == "__main__":
    # Run the experiment with config file
    experiment = run_atm_experiment_with_config()

    print(f"\n✓ Experiment '{experiment.name}' completed successfully")
    print(f"✓ Analyzed {len(experiment.scenarios)} scenarios")
