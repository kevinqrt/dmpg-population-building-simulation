import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.experiments.experiment import ExperimentRunner
from src.core.simulation.experiments.parameter_manager import parameterize_model


@parameterize_model
def setup_atm_model(env, parameters=None):

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


def run_atm_experiment():
    """Run a simple ATM experiment comparing two scenarios."""

    # Create experiment runner
    experiment = ExperimentRunner(
        name="ATM Service Analysis",
        model_builder=setup_atm_model,
        tracked_statistics=[
            ('Source', 'CustomerArrival', 'NumberCreated', 'Arrived_Customers'),
            ('Server', 'ATM', 'ScheduledUtilization', 'ATM_Util'),
            ('Server', 'ATM', 'TimeInQueue (average)', 'Queue_Time'),
        ],
        parameter_display_names={
            'arrival_rate': 'Arrival_Rate',
            'ATM.capacity': 'ATM_Count',
        }
    )

    # Scenario 1: Single ATM
    experiment.create_scenario(
        name="Standard",
        parameters={
            'arrival_rate': 0.4,
            'ATM.capacity': 1
        },
        description="Baseline configuration with 1 ATM"
    )

    # Scenario 2: Two ATMs
    experiment.create_scenario(
        name="TwoATMs",
        parameters={
            'arrival_rate': 0.4,
            'ATM.capacity': 2
        },
        description="Configuration with 2 ATMs"
    )

    # Run the experiment
    experiment.run_all(
        steps=5000,
        replications=50,
        multiprocessing=True
    )

    # Display results
    experiment.display_summary_table()

    return experiment


if __name__ == "__main__":
    experiment = run_atm_experiment()
