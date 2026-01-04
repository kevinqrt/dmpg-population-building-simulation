import numpy as np
from scipy.stats import norm, t

import src.core.global_imports as gi
from src.core.components.combiner import Combiner
from src.core.components.entity import EntityManager
from src.core.components.logistic.storage import Storage
from src.core.components.model import Model
from src.core.components.separator import Separator
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source
from src.core.components.vehicle import Vehicle


def calculate_units_utilized(units_utilized_over_time, capacity, current_time):
    """
    Compute the average units utilized based on open/closed intervals.

    :param units_utilized_over_time: List of (start_time, end_time, units) tuples
    :param capacity: Maximum capacity
    :param current_time: Current simulation time
    :return: Average units utilized
    """
    if not units_utilized_over_time:
        return 0

    total_utilization = 0
    total_time = 0

    for start, end, units in units_utilized_over_time:
        if end is None:
            end = current_time

        if end <= gi.DURATION_WARM_UP:
            continue

        if start < gi.DURATION_WARM_UP and end > gi.DURATION_WARM_UP:
            start = gi.DURATION_WARM_UP

        duration = end - start
        total_utilization += duration * min(units, capacity)
        total_time += duration

    return total_utilization / total_time if total_time > 0 else 0


def calculate_worker_utilization(simulation_time):
    """
    Calculate utilization statistics for each worker.
    Returns a list of dictionaries (one per worker).
    """
    pool = Model().worker_pool
    worker_stats = []
    for worker in pool.workers:
        utilization = (worker.total_busy_time / simulation_time) * 100 if simulation_time > 0 else 0
        worker_stats.append({
            'Type': 'Worker',
            'Name': worker.capa_id,
            'Stat': 'Allocations',
            'Value': worker.allocations
        })
        worker_stats.append({
            'Type': 'Worker',
            'Name': worker.capa_id,
            'Stat': 'TotalBusyTime',
            'Value': round(worker.total_busy_time, 2)
        })
        worker_stats.append({
            'Type': 'Worker',
            'Name': worker.capa_id,
            'Stat': 'Utilization',
            'Value': round(utilization, 2)
        })
    return worker_stats


def calculate_statistics(env) -> tuple:
    """
    Compute and return performance statistics for all major simulation components.

    Statistics per component:

    ENTITY STATISTICS:
    ------------------
    - 'NumberCreated': Total number of entities created during the simulation.
    - 'NumberDestroyed': Total number of entities removed from the system.
    - 'NumberInSystem (average)': Average number of entities present in the system.
    - 'NumberRemaining': Number of entities left in the system at simulation end.
    - 'TimeInSystem (average)': Average time entities spent in the system.
    - 'TimeInSystem (max)': Maximum observed time in system.
    - 'TimeInSystem (min)': Minimum observed time in system.

    SERVER STATISTICS:
    ------------------
    - 'EntitiesInQueue (average)': Mean queue length over time.
    - 'EntitiesInQueue (max)': Peak queue size.
    - 'EntitesInQueue (total)': Total number of entities that queued at this server.
    - 'EntitiesProcessed': Number of entities processed successfully.
    - 'NumberDowntimes': Count of downtimes recorded for the server.
    - 'ScheduledUtilization': Percentage of scheduled time the server was in use (adjusted for capacity).
    - 'StarvingTime (scheduled)': Idle time percentage (no input entities).
    - 'StarvingTime (total)': Absolute time the server was idle due to starvation.
    - 'TimeInQueue (average)': Average queue wait time.
    - 'TimeInQueue (max)': Maximum wait time experienced.
    - 'TimeProcessing (average)': Average processing duration per entity.
    - 'TimeProcessing (total)': Total time spent processing.
    - 'TotalDowntime': Total time the server was unavailable.
    - 'UnitsUtilized': Time-weighted average of units in use (adjusted for capacity).

    SINK STATISTICS:
    ----------------
    - 'NumTimesProcessed (average)': Avg. number of times entities reached the sink.
    - 'NumTimesProcessed (max)': Max number of sink arrivals per entity.
    - 'NumTimesProcessed (min)': Min number of sink arrivals per entity.
    - 'NumberEntered': Total number of entities received by the sink.
    - 'TimeInSystem (average)': Avg. time from entity creation to final sink.
    - 'TimeInSystem (max)': Max time from creation to sink.
    - 'TimeInSystem (min)': Min time from creation to sink.

    SOURCE STATISTICS:
    ------------------
    - 'NumberCreated': Number of entities this source has generated.
    - 'NumberExited': Number of entities successfully handed off.

    VEHICLE STATISTICS:
    -------------------
    - 'EntitiesInQueue (average)': Avg. number of entities waiting for transport.
    - 'EntitiesInQueue (max)': Max queue length.
    - 'EntitiesTransported': Total number of entities transported.
    - 'TimeInQueue (average)': Avg. time spent waiting for a vehicle.
    - 'TimeInQueue (max)': Max wait time before transport.
    - 'TotalTrips': Total number of trips made.
    - 'TravelTime (average)': Average trip duration.
    - 'TravelTime (total)': Total time spent in transit.
    - 'UnitsUtilized': Time-weighted average vehicle usage (adjusted for capacity).

    STORAGE STATISTICS:
    -------------------
    - 'EntitiesInQueue (average)': Avg. queue length for storage access.
    - 'EntitiesInQueue (max)': Max queue size.
    - 'NumberEntered': Total number of entities stored.
    - 'NumberExited': Total number of entities retrieved.
    - 'ScheduledUtilization': Percentage of time storage was used (adjusted for capacity).
    - 'TimeInQueue (average)': Avg. wait time for access.
    - 'TimeInQueue (max)': Max wait time observed.
    - 'TimeProcessing (average)': Average storage duration per entity.
    - 'TimeProcessing (total)': Cumulative storage duration.
    - 'UnitsUtilized': Time-weighted average number of storage units in use.
    """
    # Calculate total and effective time
    total_time = env.now
    effective_time = total_time

    if gi.DURATION_WARM_UP > 0:
        effective_time = total_time - gi.DURATION_WARM_UP

    # Entity statistics
    entity_stats = {
        'NumberCreated': EntityManager.number_created,
        'NumberDestroyed': EntityManager.number_destroyed,
        'NumberInSystem (average)': EntityManager.finalize_statistics(),
        'NumberRemaining': EntityManager.number_created - EntityManager.number_destroyed,
        'TimeInSystem (average)': EntityManager.avg_time(),
        'TimeInSystem (max)': EntityManager.max_time_in_system,
        'TimeInSystem (min)': EntityManager.min_time_in_system
    }

    # Server statistics
    server_stats = []
    for server in Server.servers:
        # Queue metrics
        avg_entities_in_queue = np.mean(server.queue_lengths) if server.queue_lengths else 0
        max_entities_in_queue = max(server.queue_lengths) if server.queue_lengths else 0
        avg_time_in_queue = np.mean(server.queue_times) if server.queue_times else 0
        max_time_in_queue = max(server.queue_times) if server.queue_times else 0

        scheduled_utilization = 0
        avg_time_processing = 0

        if server.total_entities_processed_pivot_table > 0:
            scheduled_utilization = ((server.total_processing_time_pivot_table / effective_time) * 100) / server.capacity
            avg_time_processing = server.total_processing_time_pivot_table / server.total_entities_processed_pivot_table

        scheduled_starving = 100 - scheduled_utilization
        total_starving = (scheduled_starving / 100) * server.total_processing_time_pivot_table if scheduled_utilization > 0 else 0
        units_utilized = calculate_units_utilized(server.units_utilized_over_time, server.capacity, total_time)

        server_stats.append({
            'Server': server.name,
            'EntitiesInQueue (average)': avg_entities_in_queue,
            'EntitiesInQueue (max)': max_entities_in_queue,
            'EntitiesInQueue (total)': server.number_entered_pivot_table,
            'EntitiesProcessed': server.number_exited_pivot_table,
            'NumberDowntimes': server.number_downtimes_pivot_table,
            'ScheduledUtilization': scheduled_utilization,
            'StarvingTime (scheduled)': scheduled_starving,
            'StarvingTime (total)': total_starving,
            'TimeInQueue (average)': avg_time_in_queue,
            'TimeInQueue (max)': max_time_in_queue,
            'TimeProcessing (average)': avg_time_processing,
            'TimeProcessing (total)': server.total_processing_time_pivot_table,
            'TotalDowntime': server.total_downtime_pivot_table,
            'UnitsUtilized': units_utilized
        })

    # Sink statistics
    sink_stats = {}
    for sink in Sink.sinks:
        if sink.tally_statistic.values:
            tally_min, tally_max, tally_avg = sink.tally_statistic.calculate_statistics()
        else:
            tally_min, tally_max, tally_avg = None, None, None

        avg_time_in_system = (sink.total_time_in_system / sink.entities_processed
                              if sink.entities_processed > 0 else 0)
        sink_stats[sink.name] = {
            'NumTimesProcessed (average)': tally_avg,
            'NumTimesProcessed (max)': tally_max,
            'NumTimesProcessed (min)': tally_min,
            'NumberEntered': sink.number_entered_pivot_table,
            'TimeInSystem (average)': avg_time_in_system,
            'TimeInSystem (max)': sink.max_time_in_system_pivot_table,
            'TimeInSystem (min)': sink.min_time_in_system_pivot_table if sink.entities_processed > 0 else None,
        }

    # Source statistics
    source_stats = {}
    for source in Source.sources:
        source_stats[source.name] = {
            'NumberCreated': source.entities_created_pivot_table,
            'NumberExited': source.number_exited_pivot_table,
        }

    # Vehicle statistics
    vehicle_stats = []
    for vehicle in Vehicle.vehicles:
        current_simulation_time = env.now
        avg_entities_in_queue = np.mean(vehicle.queue_lengths) if vehicle.queue_lengths else 0
        max_entities_in_queue = max(vehicle.queue_lengths) if vehicle.queue_lengths else 0
        avg_time_in_queue = np.mean(vehicle.queue_times) if vehicle.queue_times else 0
        max_time_in_queue = max(vehicle.queue_times) if vehicle.queue_times else 0

        scheduled_utilization = 0
        total_starving = 0
        scheduled_starving = 0
        if env.now > gi.DURATION_WARM_UP:
            scheduled_utilization = ((vehicle.total_processing_time_pivot_table / effective_time) * 100) / vehicle.resource.capacity
            scheduled_starving = 100 - scheduled_utilization
            total_starving = (scheduled_starving / 100) * vehicle.total_processing_time_pivot_table if scheduled_utilization > 0 else 0

        avg_travel_time = vehicle.total_travel_time / vehicle.total_trips if vehicle.total_trips > 0 else 0
        units_utilized = calculate_units_utilized(vehicle.time_utilized_over_time, vehicle.resource.capacity, current_simulation_time)

        vehicle_stats.append({
            'Vehicle': vehicle.name,
            'EntitiesInQueue (average)': avg_entities_in_queue,
            'EntitiesInQueue (max)': max_entities_in_queue,
            'EntitiesInQueue (total)': vehicle.number_entered_pivot_table,
            'EntitiesTransported': vehicle.entities_transported,
            'NumberDowntimes': vehicle.number_downtimes_pivot_table,
            'ScheduledUtilization': scheduled_utilization,
            'StarvingTime (scheduled)': scheduled_starving,
            'StarvingTime (total)': total_starving,
            'TimeInQueue (average)': avg_time_in_queue,
            'TimeInQueue (max)': max_time_in_queue,
            'TotalDowntimes': vehicle.total_downtime_pivot_table,
            'TotalTrips': vehicle.total_trips,
            'TravelTime (average)': avg_travel_time,
            'TravelTime (total)': vehicle.total_travel_time,
            'UnitsUtilized': units_utilized
        })

    # Storage statistics
    storage_stats = []
    for storage in Storage.storages:
        current_simulation_time = env.now
        avg_entities_in_queue = np.mean(storage.queue_lengths) if storage.queue_lengths else 0
        max_entities_in_queue = max(storage.queue_lengths) if storage.queue_lengths else 0
        avg_time_in_queue = np.mean(storage.queue_times) if storage.queue_times else 0
        max_time_in_queue = max(storage.queue_times) if storage.queue_times else 0

        scheduled_utilization = 0
        avg_time_processing = 0
        total_starving = 0
        scheduled_starving = 0
        if env.now > gi.DURATION_WARM_UP:
            scheduled_utilization = ((storage.total_processing_time_pivot_table / effective_time) * 100) / storage.capacity
            avg_time_processing = (storage.total_processing_time_pivot_table / storage.total_entities_processed_pivot_table
                                   if storage.total_entities_processed_pivot_table > 0 else 0)
            scheduled_starving = 100 - scheduled_utilization
            total_starving = (scheduled_starving / 100) * storage.total_processing_time_pivot_table if scheduled_utilization > 0 else 0

        units_utilized = calculate_units_utilized(storage.units_utilized_over_time, storage.capacity, env.now)

        storage_stats.append({
            'Storage': storage.name,
            'EntitiesInQueue (average)': avg_entities_in_queue,
            'EntitiesInQueue (max)': max_entities_in_queue,
            'EntitiesInQueue (total)': storage.number_entered_pivot_table,
            'EntitiesProcessed': storage.total_entities_processed_pivot_table,
            'ScheduledUtilization': scheduled_utilization,
            'StarvingTime (scheduled)': scheduled_starving,
            'StarvingTime (total)': total_starving,
            'TimeInQueue (average)': avg_time_in_queue,
            'TimeInQueue (max)': max_time_in_queue,
            'TimeProcessing (average)': avg_time_processing,
            'TimeProcessing (total)': storage.total_processing_time_pivot_table,
            'UnitsUtilized': units_utilized
        })

    # Separator statistics
    separator_stats = []
    for separator in Separator.separators:
        avg_entities_in_queue = np.mean(separator.queue_lengths) if separator.queue_lengths else 0
        max_entities_in_queue = max(separator.queue_lengths) if separator.queue_lengths else 0
        avg_time_in_queue = np.mean(separator.queue_times) if separator.queue_times else 0
        max_time_in_queue = max(separator.queue_times) if separator.queue_times else 0

        scheduled_utilization = 0
        avg_time_processing = 0
        scheduled_starving = 0
        total_starving = 0
        if separator.total_entities_processed_pivot_table > 0:
            scheduled_utilization = ((separator.total_processing_time_pivot_table / effective_time) * 100) / separator.capacity
            avg_time_processing = separator.total_processing_time_pivot_table / separator.total_entities_processed_pivot_table

            scheduled_starving = 100 - scheduled_utilization
            total_starving = (scheduled_starving / 100) * separator.total_processing_time_pivot_table if scheduled_utilization > 0 else 0

        units_utilized = calculate_units_utilized(separator.units_utilized_over_time, separator.capacity, total_time)

        separator_stats.append({
            'Separator': separator.name,
            'EntitiesInQueue (average)': avg_entities_in_queue,
            'EntitiesInQueue (max)': max_entities_in_queue,
            'EntitiesInQueue (total)': separator.number_entered_pivot_table,
            'EntitiesProcessed': separator.total_entities_processed_pivot_table,
            'NumberDowntimes': separator.number_downtimes_pivot_table,
            'ScheduledUtilization': scheduled_utilization,
            'StarvingTime (scheduled)': scheduled_starving,
            'StarvingTime (total)': total_starving,
            'TimeInQueue (average)': avg_time_in_queue,
            'TimeInQueue (max)': max_time_in_queue,
            'TimeProcessing (average)': avg_time_processing,
            'TimeProcessing (total)': separator.total_processing_time_pivot_table,
            'TotalDowntime': separator.total_downtime_pivot_table,
            'UnitsUtilized': units_utilized
        })

    # Combiner statistics (falls Combiner ähnlich aufgebaut ist)
    combiner_stats = []
    for combiner in Combiner.combiners:
        avg_parents_in_queue = np.mean(combiner.parent_queue_lengths) if combiner.parent_queue_lengths else 0
        max_parents_in_queue = max(combiner.parent_queue_lengths) if combiner.parent_queue_lengths else 0
        avg_members_in_queue = np.mean(combiner.member_queue_lengths) if combiner.member_queue_lengths else 0
        max_members_in_queue = max(combiner.member_queue_lengths) if combiner.member_queue_lengths else 0

        members_avg_time_in_queue = np.mean(combiner.member_queue_times) if combiner.member_queue_times else 0
        members_max_time_in_queue = max(combiner.member_queue_times) if combiner.member_queue_times else 0

        parents_avg_time_in_queue = np.mean(combiner.parent_queue_times) if combiner.parent_queue_times else 0
        parents_max_time_in_queue = max(combiner.parent_queue_times) if combiner.parent_queue_times else 0

        scheduled_utilization = 0
        avg_time_processing = 0
        scheduled_starving = 0
        total_starving = 0
        if combiner.total_entities_processed_pivot_table > 0:
            scheduled_utilization = ((combiner.total_processing_time_pivot_table / effective_time) * 100) / combiner.capacity
            avg_time_processing = combiner.total_processing_time_pivot_table / combiner.total_entities_processed_pivot_table
            scheduled_starving = 100 - scheduled_utilization
            total_starving = (scheduled_starving / 100) * combiner.total_processing_time_pivot_table if scheduled_utilization > 0 else 0

        units_utilized = calculate_units_utilized(combiner.units_utilized_over_time, combiner.capacity, total_time)

        combiner_stats.append({
            'Combiner': combiner.name,
            'EntitiesInQueue (total)': combiner.total_queue_length,
            'EntitiesProcessed': combiner.total_entities_processed_pivot_table,
            'NumberDowntimes': combiner.number_downtimes_pivot_table,
            'MembersEntered': combiner.number_members_entered_pivot_table,
            'MembersInQueue (average)': avg_members_in_queue,
            'MembersInQueue (max)': max_members_in_queue,
            'Members TimeInQueue (average)': members_avg_time_in_queue,
            'Members TimeInQueue (max)': members_max_time_in_queue,
            'ParentsEntered': combiner.number_parents_entered_pivot_table,
            'ParentsInQueue (average)': avg_parents_in_queue,
            'ParentsInQueue (max)': max_parents_in_queue,
            'Parents TimeInQueue (average)': parents_avg_time_in_queue,
            'Parents TimeInQueue (max)': parents_max_time_in_queue,
            'ScheduledUtilization': scheduled_utilization,
            'StarvingTime (scheduled)': scheduled_starving,
            'StarvingTime (total)': total_starving,
            'TimeProcessing (average)': avg_time_processing,
            'TimeProcessing (total)': combiner.total_processing_time_pivot_table,
            'TotalDowntime': combiner.total_downtime_pivot_table,
            'UnitsUtilized': units_utilized
        })

    return entity_stats, server_stats, sink_stats, source_stats, vehicle_stats, storage_stats, separator_stats, combiner_stats


def calculate_all_stats(all_entity_stats, all_server_stats, all_sink_stats, all_source_stats,
                        all_vehicle_stats, all_storage_stats, all_separator_stats, all_combiner_stats,
                        entity_stat_names, server_stat_names, sink_stat_names,
                        source_stat_names, vehicle_stat_names, storage_stat_names, separator_stat_names, combiner_stat_names, confidence=0.95) -> list:
    """
    Aggregate and flatten statistics from multiple replications.
    all_separator_stats, all_combiner_stats,

     separator_stat_names, combiner_stat_names,
    """
    def calculate_aggregate_stats(values) -> tuple:
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if not numeric_values:
            return None, None, None, None

        # TBR -> assert ?
        n = len(numeric_values)
        if n == 1:
            return numeric_values[0], numeric_values[0], numeric_values[0], 0

        if not (0 < confidence < 1):
            raise ValueError("Confidence level must be between 0 and 1 (exclusive), e.g., 0.95 for 95%.")

        avg = np.mean(numeric_values)
        min_val = np.min(numeric_values)
        max_val = np.max(numeric_values)
        std_dev = np.std(numeric_values, ddof=1)  # Sample standard deviation (ddof=1 for unbiased estimator)

        # if n > 30 use normal distribution approximation (Z-distribution)
        # else use t-distribution for small samples
        half_width = norm.ppf((1 + confidence) / 2) * (std_dev / np.sqrt(n)) if n > 30 \
            else t.ppf((1 + confidence) / 2, df=n - 1) * (std_dev / np.sqrt(n))

        # half_width = 1.96 * (np.std(numeric_values) / np.sqrt(len(numeric_values)))     # 1.96 = critical value of 95% confidence interval

        return avg, min_val, max_val, half_width

    def flatten_stats(stats, component_type, stat_names, is_entity=False) -> list:
        flattened = []
        for component_name, stat_values in stats.items():
            for stat_name in stat_names:
                values = stat_values.get(stat_name, {}) if is_entity else stat_values.get(stat_name)
                if values:
                    if is_entity:
                        avg, min_val, max_val, half_width = values
                    else:
                        avg, min_val, max_val, half_width = values[0], values[1], values[2], values[3]
                    flattened.append({
                        'Type': component_type,
                        'Name': component_name,
                        'Stat': stat_name,
                        'Average': round(avg, 4) if avg is not None else None,
                        'Minimum': round(min_val, 4) if min_val is not None else None,
                        'Maximum': round(max_val, 4) if max_val is not None else None,
                        'Half-Width': round(half_width, 4) if half_width is not None else None
                    })
        return flattened

    def aggregate_stats(entity_stats: dict[str, list[dict[str, any]]], stat_names: list[str]) \
            -> dict[str, dict[str, any]]:
        """
        Aggregates statistics for a given entity stats dictionary.

        :param entity_stats: A dictionary where key is an entity name and value is a list of stats.
        :param stat_names: A list of stat names to calculate aggregates for.
        :return: A dictionary with aggregated stats for each entity.
        """
        return {
            entity_name: {
                key: calculate_aggregate_stats([stat[key] for stat in stats_list])
                for key in stat_names
            }
            for entity_name, stats_list in entity_stats.items() if stats_list
        }

    # Aggregate entity stats
    entity_aggregate_stats = {stat: calculate_aggregate_stats([run[stat] for run in all_entity_stats])
                              for stat in entity_stat_names}
    modified_entity_stats = {'Entity': {}}
    for stat_name, values in entity_aggregate_stats.items():
        modified_entity_stats['Entity'][stat_name] = values

    aggregate_server_stats = aggregate_stats(all_server_stats, server_stat_names)
    aggregate_sink_stats = aggregate_stats(all_sink_stats, sink_stat_names)
    aggregate_source_stats = aggregate_stats(all_source_stats, source_stat_names)
    aggregate_vehicle_stats = aggregate_stats(all_vehicle_stats, vehicle_stat_names)
    aggregate_storage_stats = aggregate_stats(all_storage_stats, storage_stat_names)
    aggregate_separator_stats = aggregate_stats(all_separator_stats, separator_stat_names)
    aggregate_combiner_stats = aggregate_stats(all_combiner_stats, combiner_stat_names)

    flattened_stats = []
    flattened_stats.extend(flatten_stats(modified_entity_stats, 'Entity', entity_stat_names, is_entity=True))
    flattened_stats.extend(flatten_stats(aggregate_server_stats, 'Server', server_stat_names))
    flattened_stats.extend(flatten_stats(aggregate_sink_stats, 'Sink', sink_stat_names))
    flattened_stats.extend(flatten_stats(aggregate_source_stats, 'Source', source_stat_names))
    flattened_stats.extend(flatten_stats(aggregate_vehicle_stats, 'Vehicle', vehicle_stat_names))
    flattened_stats.extend(flatten_stats(aggregate_storage_stats, 'Storage', storage_stat_names))
    flattened_stats.extend(flatten_stats(aggregate_separator_stats, 'Separator', separator_stat_names))
    flattened_stats.extend(flatten_stats(aggregate_combiner_stats, 'Combiner', combiner_stat_names))

    return flattened_stats
