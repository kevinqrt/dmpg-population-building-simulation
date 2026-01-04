from src.core.components.date_time import DateTime
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_replications
import src.core.config as cfg


def model5_1(env):
    """Model 5.1 with configuration-driven parameters."""

    # Source with configured arrival rate
    source = Source(
        env,
        "Source",
        creation_time_distribution_with_parameters=cfg.get_distribution('source.arrival_rate')
    )

    # Servers with configured processing times and capacities
    placement = Server(
        env,
        "Placement",
        processing_time_distribution_with_parameters=cfg.get_distribution('servers.placement.processing_time'),
        capacity=cfg.get_param('servers.placement.capacity', default=1)
    )

    inspection = Server(
        env,
        "Inspection",
        processing_time_distribution_with_parameters=cfg.get_distribution('servers.inspection.processing_time'),
        capacity=cfg.get_param('servers.inspection.capacity', default=1)
    )

    # Sinks
    good_parts = Sink(env, "Goodparts")
    bad_parts = Sink(env, "Badparts")

    source.connect(placement)
    placement.connect(inspection)
    inspection.connect(
        good_parts,
        probability=cfg.get_param('routing.good_parts_probability')
    )
    inspection.connect(
        bad_parts,
        probability=cfg.get_param('routing.bad_parts_probability')
    )


def main():
    run_replications(
        model=model5_1,
        steps=DateTime.map_time_to_steps(hours=1200),
        warm_up=DateTime.map_time_to_steps(hours=200),
        num_replications=25,
        multiprocessing=True,
        config="model5_1_config.yaml"
    )


if __name__ == '__main__':
    main()
