import logging
import time
from datetime import timedelta

# Variables for replication timing
seconds_previous_computations = 0
iterations_printed = 0


def get_percentage_and_computingtimes(computing_time_start, i, num_replications) -> tuple:
    """
    Compute timing metrics for replication progress.
    """
    global seconds_previous_computations, iterations_printed
    iterations_printed += 1
    seconds_computed = time.time() - computing_time_start
    seconds_computed_iteration = seconds_computed - seconds_previous_computations
    seconds_computed_iteration_average = seconds_computed / iterations_printed
    seconds_previous_computations = seconds_computed
    percentage = round((i + 1) / num_replications * 100)
    total_seconds_to_complete = seconds_computed / (percentage / 100)
    return (
        f"{percentage:>3}%",
        f"[time computed] {str(timedelta(seconds=seconds_computed)):<15}",
        f"[time to compute] {str(timedelta(seconds=total_seconds_to_complete - seconds_computed)):<15}",
        f"[time prediction] {str(timedelta(seconds=total_seconds_to_complete)):<15}",
        f"[time iteration] {str(timedelta(seconds=seconds_computed_iteration)):<15}",
        f"[time avg. iteration] {str(timedelta(seconds=seconds_computed_iteration_average)):<15}"
    )


def print_stats(i, num_replications, start, tenth_percentage) -> None:
    """
    Print replication progress information.
    """
    if tenth_percentage == 0 or (i + 1) % tenth_percentage == 0:
        ct = get_percentage_and_computingtimes(start, i, num_replications)
        logging.info(f"{ct[0]} replication {i + 1}/{num_replications}\t{ct[1]}\t{ct[2]}\t{ct[3]}\t{ct[4]}\t{ct[5]}")


def get_upper_and_lower_bound(vehicle, calling_object, destination, to_move):
    if not vehicle.idle:
        lower_bound = vehicle.lower_bound
        upper_bound = vehicle.upper_bound
    elif vehicle.position == vehicle.home_point.position and not to_move:
        lower_bound = vehicle.position[1]
        upper_bound = vehicle.position[1]
    else:
        lower_bound, upper_bound = calc_upper_and_lower_bound(vehicle, calling_object, destination)

    return lower_bound, upper_bound


def calc_upper_and_lower_bound(vehicle, calling_object, destination):
    try:
        postions = [vehicle.position[1], calling_object.position[1], destination.position[1]]

        lower_bound = min(postions)
        upper_bound = max(postions)
    except Exception:
        pass

    return lower_bound, upper_bound
