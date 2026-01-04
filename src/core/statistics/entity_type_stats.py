import simpy

from src.core.components.combiner import Combiner
from src.core.components.entity import EntityManager
from src.core.components.logistic.storage import Storage
from src.core.components.separator import Separator
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.components.vehicle import Vehicle


def format_entity_type_stats(entity_type_stats_dict, component_type: str, component_name: str) -> list:
    """
    Converts a nested entity-type statistics dictionary into a list of dictionaries formatted like general stats.
    """
    output = []
    stat_names = set()

    for stats in entity_type_stats_dict.values():
        stat_names.update(stats.keys())

    for stat_name in stat_names:
        row = {
            'Type': component_type,
            'Name': component_name,
            'Stat': stat_name,
            'Value': 0.0
        }
        for entity_type, stats in entity_type_stats_dict.items():
            value = stats.get(stat_name, 0.0)
            if isinstance(value, list):
                value = value[0] if len(value) > 0 else 0.0
            row[entity_type] = round(value, 4)
        output.append(row)

    return output


def collect_all_entity_type_stats(env: simpy.Environment):
    """
    Collects all entity_type_stats from different components (Source, Sink, Server).
    Returns a list that can be processed using store_entity_type_stats.
    """
    all_entity_type_rows = []

    # Entity
    entity_stats_rows = format_entity_type_stats(
        EntityManager.entity_type_stats,
        component_type="Entity",
        component_name="Entity"
    )
    all_entity_type_rows.extend(entity_stats_rows)

    # Source
    for source in Source.sources:
        source_stats = format_entity_type_stats(
            source.entity_type_stats_source,
            component_type="Source",
            component_name=source.name
        )
        all_entity_type_rows.extend(source_stats)

    # Sink
    for sink in Sink.sinks:
        sink_stats = format_entity_type_stats(
            sink.entity_type_stats_component,
            component_type="Sink",
            component_name=sink.name
        )
        all_entity_type_rows.extend(sink_stats)

    # Server
    for server in Server.servers:
        server.finalize_statistics_per_entity_type(env.now)
        server_stats = format_entity_type_stats(
            server.entity_type_stats_component,
            component_type="Server",
            component_name=server.name
        )
        all_entity_type_rows.extend(server_stats)

    # Vehicle
    for vehicle in Vehicle.vehicles:
        vehicle.finalize_statistics_per_entity_type(env.now)
        vehicle_stats = format_entity_type_stats(
            vehicle.entity_types_vehicle,
            component_type="Vehicle",
            component_name=vehicle.name
        )
        all_entity_type_rows.extend(vehicle_stats)

    # Storage
    for storage in Storage.storages:
        storage.finalize_statistics_per_entity_type(env.now)
        storage_stats = format_entity_type_stats(
            storage.entity_types_storage,
            component_type="Storage",
            component_name=storage.name
        )
        all_entity_type_rows.extend(storage_stats)

    # Combiner
    for combiner in Combiner.combiners:
        combiner.finalize_statistics_per_entity_type(env.now)
        combiner_stats = format_entity_type_stats(
            combiner.entity_type_stats_combiner,
            component_type="Combiner",
            component_name=combiner.name
        )
        all_entity_type_rows.extend(combiner_stats)

    # Separator
    for separator in Separator.separators:
        separator.finalize_statistics_per_entity_type(env.now)
        separator_stats = format_entity_type_stats(
            separator.entity_type_stats_separator,
            component_type="Separator",
            component_name=separator.name
        )
        all_entity_type_rows.extend(separator_stats)

    return all_entity_type_rows
