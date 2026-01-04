from __future__ import annotations
from typing import Protocol, Any, List, Tuple
import logging
import numpy as np

from src.core.components.date_time import DateTime
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY
from src.core.utils.helper import round_value


# Component protocols
class HasBasicFields(Protocol):
    """Base fields for all components."""
    name: str
    env: Any


class HasQueueFields(HasBasicFields, Protocol):
    """Components with queue statistics."""
    queue_lengths: List[int]
    queue_times: List[float]


class HasProcessingFields(HasBasicFields, Protocol):
    """Components with processing statistics."""
    capacity: int
    total_entities_processed_pivot_table: int
    total_processing_time_pivot_table: float
    units_utilized_over_time: List[Tuple[float, float, int]]


class HasStandardFields(HasQueueFields, HasProcessingFields, Protocol):
    """Standard server/separator/storage fields."""
    number_downtimes_pivot_table: int
    number_entered_pivot_table: int
    number_exited_pivot_table: int
    total_downtime_pivot_table: float


class HasSinkFields(HasBasicFields, Protocol):
    """Sink statistics fields."""
    tally_statistic: Any
    number_entered_pivot_table: int
    total_time_in_system: float
    entities_processed: int
    max_time_in_system_pivot_table: float
    min_time_in_system_pivot_table: float


class HasCombinerFields(HasQueueFields, HasProcessingFields, Protocol):
    """Combiner-specific fields."""
    parent_queue_lengths: List[int]
    parent_queue_times: List[float]
    member_queue_lengths: List[int]
    member_queue_times: List[float]
    number_downtimes_pivot_table: int
    number_members_entered_pivot_table: int
    number_parents_entered_pivot_table: int
    total_queue_length: int
    total_downtime_pivot_table: float


class HasVehicleFields(HasQueueFields, Protocol):
    """Vehicle-specific fields."""
    entities_transported: int
    total_trips: int
    total_travel_time: float
    total_processing_time_pivot_table: float
    number_entered_pivot_table: int
    number_downtimes_pivot_table: int
    total_downtime_pivot_table: float
    time_utilized_over_time: List[Tuple[float, float, int]]
    resource: Any  # .capacity


# Helper functions
def _calculate_queue_metrics(queue_lengths: List[int], queue_times: List[float]) -> tuple[float, int, float, float]:
    """Calculate common queue metrics."""
    avg_entities = float(np.mean(queue_lengths)) if queue_lengths else 0.0
    max_entities = int(max(queue_lengths)) if queue_lengths else 0
    avg_time = float(np.mean(queue_times)) if queue_times else 0.0
    max_time = float(max(queue_times)) if queue_times else 0.0
    return avg_entities, max_entities, avg_time, max_time


def _calculate_utilization_metrics(processing_time: float, processed_count: int, effective_time: float, capacity: int) -> tuple[float, float, float, float]:
    """Calculate utilization and starving metrics."""
    if processed_count > 0 and effective_time > 0:
        avg_processing = processing_time / processed_count
        scheduled_utilization = ((processing_time / effective_time) * 100) / capacity
    else:
        avg_processing = 0.0
        scheduled_utilization = 0.0

    scheduled_starving = 100.0 - scheduled_utilization
    total_starving = (scheduled_starving / 100.0) * processing_time if scheduled_utilization > 0 else 0.0
    return avg_processing, scheduled_utilization, scheduled_starving, total_starving


def _safe_log(msg: str, timestamp: float) -> None:
    """Safe logging that doesn't disrupt simulation."""
    try:
        if logging.root.level <= logging.TRACE:
            logging.log(logging.TRACE, ENTITY_PROCESSING_LOG_ENTRY.format(msg, DateTime.get(timestamp)))
    except Exception:
        pass


# Main logging functions
def log_standard_component_statistics(comp: HasStandardFields, component_type: str, *, effective_time: float, total_time: float) -> None:
    """Log statistics for Server/Separator/Storage components (shared logic)."""
    from src.core.statistics.stats import calculate_units_utilized

    try:
        avg_entities_in_queue, max_entities_in_queue, avg_time_in_queue, max_time_in_queue = \
            _calculate_queue_metrics(comp.queue_lengths, comp.queue_times)

        processed = int(comp.total_entities_processed_pivot_table)
        time_proc_total = float(comp.total_processing_time_pivot_table)
        avg_time_proc, scheduled_utilization, scheduled_starving, total_starving = \
            _calculate_utilization_metrics(time_proc_total, processed, effective_time, comp.capacity)

        #units_utilized = float(calculate_units_utilized(comp.units_utilized_over_time, comp.capacity, total_time))
        #units_allocated = getattr(comp, 'units_allocated', 0.0)
        #units_scheduled = getattr(comp, 'units_scheduled', 0.0)

        # Build component-specific message
        base_fields = (
            f"EntitiesInQueueAvg={round_value(avg_entities_in_queue)}, "
            f"EntitiesInQueueMax={max_entities_in_queue}, "
            f"ScheduledUtilization={round_value(scheduled_utilization)}, "
            f"StarvingScheduled={round_value(scheduled_starving)}, "
            f"StarvingTotal={round_value(total_starving)}, "
            f"TimeInQueueAvg={round_value(avg_time_in_queue)}, "
            f"TimeInQueueMax={round_value(max_time_in_queue)}, "
            f"TimeProcessingAvg={round_value(avg_time_proc)}, "
            f"TimeProcessingTotal={round_value(time_proc_total)}, "
            f"UnitsUtilized={round_value(units_utilized)}"
        )

        if component_type in ["Server", "Separator"]:
            specific_fields = (
                f"NumberDowntimes={comp.number_downtimes_pivot_table}, "
                f"NumberEntered={comp.number_entered_pivot_table}, "
                f"NumberExited={comp.number_exited_pivot_table}, "
                f"TotalDowntime={round_value(comp.total_downtime_pivot_table)}, "
                f"UnitsAllocated={round_value(units_allocated)}, "
                f"UnitsScheduled={round_value(units_scheduled)}, "
            )
        else:  # Storage
            specific_fields = f"EntitiesProcessed={processed}, "

        msg = f"[{component_type}Statistics] {component_type}={comp.name}, {specific_fields}{base_fields}"
        _safe_log(msg, comp.env.now)
    except Exception:
        pass


def log_server_statistics(comp: HasStandardFields, *, effective_time: float, total_time: float) -> None:
    """Log server statistics."""
    log_standard_component_statistics(comp, "Server", effective_time=effective_time, total_time=total_time)


def log_separator_statistics(comp: HasStandardFields, *, effective_time: float, total_time: float) -> None:
    """Log separator statistics."""
    log_standard_component_statistics(comp, "Separator", effective_time=effective_time, total_time=total_time)


def log_storage_statistics(comp: HasStandardFields, *, effective_time: float, total_time: float) -> None:
    """Log storage statistics."""
    log_standard_component_statistics(comp, "Storage", effective_time=effective_time, total_time=total_time)


def log_sink_statistics(comp: HasSinkFields) -> None:
    """Log sink statistics."""
    try:
        if getattr(comp.tally_statistic, "values", None):
            t_min, t_max, t_avg = comp.tally_statistic.calculate_statistics()
        else:
            t_min = t_max = t_avg = None

        processed = int(comp.entities_processed)
        avg_time_in_system = (comp.total_time_in_system / processed) if processed > 0 else 0.0
        time_in_system_max = float(comp.max_time_in_system_pivot_table)
        time_in_system_min = comp.min_time_in_system_pivot_table if processed > 0 else None

        def fmt_optional(x):
            return "-" if x is None else round_value(x)

        msg = (
            f"[SinkStatistics] Sink={comp.name}, "
            f"NumTimesProcessedAvg={fmt_optional(t_avg)}, "
            f"NumTimesProcessedMax={fmt_optional(t_max)}, "
            f"NumTimesProcessedMin={fmt_optional(t_min)}, "
            f"NumberEntered={comp.number_entered_pivot_table}, "
            f"TimeInSystemAvg={round_value(avg_time_in_system)}, "
            f"TimeInSystemMax={round_value(time_in_system_max)}, "
            f"TimeInSystemMin={fmt_optional(time_in_system_min)}"
        )
        _safe_log(msg, comp.env.now)
    except Exception:
        pass


def log_combiner_statistics(comp: HasCombinerFields, *, effective_time: float, total_time: float) -> None:
    """Log combiner statistics."""
    from src.core.statistics.stats import calculate_units_utilized

    try:
        avg_parents_in_queue, max_parents_in_queue, parents_avg_time_in_queue, parents_max_time_in_queue = \
            _calculate_queue_metrics(comp.parent_queue_lengths, comp.parent_queue_times)
        avg_members_in_queue, max_members_in_queue, members_avg_time_in_queue, members_max_time_in_queue = \
            _calculate_queue_metrics(comp.member_queue_lengths, comp.member_queue_times)

        processed = int(comp.total_entities_processed_pivot_table)
        time_proc_total = float(comp.total_processing_time_pivot_table)
        avg_time_proc, scheduled_utilization, scheduled_starving, total_starving = \
            _calculate_utilization_metrics(time_proc_total, processed, effective_time, comp.capacity)

        units_utilized = float(calculate_units_utilized(comp.units_utilized_over_time, comp.capacity, total_time))

        msg = (
            f"[CombinerStatistics] Combiner={comp.name}, "
            f"EntitiesInQueueTotal={comp.total_queue_length}, "
            f"EntitiesProcessed={processed}, "
            f"MembersEntered={comp.number_members_entered_pivot_table}, "
            f"MembersInQueueAvg={round_value(avg_members_in_queue)}, "
            f"MembersInQueueMax={max_members_in_queue}, "
            f"MembersTimeInQueueAvg={round_value(members_avg_time_in_queue)}, "
            f"MembersTimeInQueueMax={round_value(members_max_time_in_queue)}, "
            f"NumberDowntimes={comp.number_downtimes_pivot_table}, "
            f"ParentsEntered={comp.number_parents_entered_pivot_table}, "
            f"ParentsInQueueAvg={round_value(avg_parents_in_queue)}, "
            f"ParentsInQueueMax={max_parents_in_queue}, "
            f"ParentsTimeInQueueAvg={round_value(parents_avg_time_in_queue)}, "
            f"ParentsTimeInQueueMax={round_value(parents_max_time_in_queue)}, "
            f"ScheduledUtilization={round_value(scheduled_utilization)}, "
            f"StarvingScheduled={round_value(scheduled_starving)}, "
            f"StarvingTotal={round_value(total_starving)}, "
            f"TimeProcessingAvg={round_value(avg_time_proc)}, "
            f"TimeProcessingTotal={round_value(time_proc_total)}, "
            f"TotalDowntime={round_value(comp.total_downtime_pivot_table)}, "
            f"UnitsUtilized={round_value(units_utilized)}"
        )
        _safe_log(msg, comp.env.now)
    except Exception:
        pass


def log_vehicle_statistics(comp: HasVehicleFields, *, effective_time: float, total_time: float) -> None:
    """Log vehicle statistics."""
    from src.core.statistics.stats import calculate_units_utilized

    try:
        avg_entities_in_queue, max_entities_in_queue, avg_time_in_queue, max_time_in_queue = \
            _calculate_queue_metrics(comp.queue_lengths, comp.queue_times)

        time_proc_total = float(comp.total_processing_time_pivot_table)
        avg_time_proc, scheduled_utilization, scheduled_starving, total_starving = \
            _calculate_utilization_metrics(time_proc_total, comp.entities_transported, effective_time, comp.resource.capacity)

        avg_travel_time = comp.total_travel_time / comp.total_trips if comp.total_trips > 0 else 0.0
        units_utilized = float(calculate_units_utilized(comp.time_utilized_over_time, comp.resource.capacity, total_time))

        msg = (
            f"[VehicleStatistics] Vehicle={comp.name}, "
            f"EntitiesInQueueAvg={round_value(avg_entities_in_queue)}, "
            f"EntitiesInQueueMax={max_entities_in_queue}, "
            f"EntitiesTransported={comp.entities_transported}, "
            f"NumberDowntimes={comp.number_downtimes_pivot_table}, "
            f"ScheduledUtilization={round_value(scheduled_utilization)}, "
            f"StarvingScheduled={round_value(scheduled_starving)}, "
            f"StarvingTotal={round_value(total_starving)}, "
            f"TimeInQueueAvg={round_value(avg_time_in_queue)}, "
            f"TimeInQueueMax={round_value(max_time_in_queue)}, "
            f"TotalDowntime={round_value(comp.total_downtime_pivot_table)}, "
            f"TotalTrips={comp.total_trips}, "
            f"TravelTimeAvg={round_value(avg_travel_time)}, "
            f"TravelTimeTotal={round_value(comp.total_travel_time)}, "
            f"UnitsUtilized={round_value(units_utilized)}"
        )
        _safe_log(msg, comp.env.now)
    except Exception:
        pass
