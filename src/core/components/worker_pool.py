import simpy
import logging
import pandas as pd
from typing import List, Dict, Optional, Union, Any, Set, Iterator
from src.core.components.date_time import DateTime
from src.core.components.model import Model
import src.core.config as cfg

# Constants
TABLE_WIDTH: int = 80


class Worker:
    """
    Represents a worker token with a unique id and tracks utilization.
    """
    def __init__(self, id: str) -> None:
        self.id: str = id
        self.allocations: int = 0
        self.total_busy_time: float = 0.0
        self.busy_since: Optional[float] = None
        self.busy_with: Optional[str] = None

    def start_assignment(self, server_name: str, start_time: float) -> None:
        """Record the start of an assignment to a specific server"""
        self.allocations += 1
        if self.busy_since is not None:
            self.total_busy_time += start_time - self.busy_since

        self.busy_since = start_time
        self.busy_with = server_name

    def end_assignment(self, server_name: str, end_time: float) -> float:
        """End an assignment and calculate busy time"""
        if self.busy_since is None or self.busy_with != server_name:
            logging.warning(f"Worker {self.id} wasn't assigned to {server_name} but was asked to end assignment")
            return 0.0

        duration: float = end_time - self.busy_since
        self.total_busy_time += duration
        self.busy_since = None
        self.busy_with = None
        return duration

    def __repr__(self) -> str:
        return f"Worker({self.id})"


class WorkerPool:
    """
    Represents a shared worker pool whose available workers are updated
    dynamically according to a WorkScheduleWeek.
    Optionally, a specific list of workers can be provided.
    """
    def __init__(self, env: simpy.Environment, work_schedule: Any, workers: Optional[List[Worker]] = None) -> None:
        self.env: simpy.Environment = env
        self.work_schedule: Any = work_schedule
        self.workers: List[Worker] = []

        # If a list of workers is provided, use it; otherwise, create a generic list
        if workers is not None:
            self.workers = workers
        else:
            # Fallback: create a number of generic workers equal to the capacity of the shift
            shifts, _ = self.work_schedule.get()
            default_cap: Union[int, Dict[str, int]] = shifts[0][2] if shifts else 0

            # If capacity is given as an int, we create workers with id "Worker_1", etc.
            if isinstance(default_cap, int):
                self.workers = [Worker(f"Worker_{i + 1}") for i in range(default_cap)]
            else:
                total: int = sum(default_cap.values())
                self.workers = [Worker(f"Worker_{i + 1}") for i in range(total)]

        # Use a FilterStore so that servers can request a worker by filtering on its id
        self.store: simpy.FilterStore = simpy.FilterStore(env)
        self.store.items = list(self.workers)
        self.worker_locks: Dict[str, simpy.Resource] = {worker.id: simpy.Resource(env, capacity=1) for worker in self.workers}
        self.env.process(self.manage_workers())

    def manage_workers(self) -> Iterator[simpy.events.Event]:
        """
        Resets the pool's available workers according to the work schedule.
        """
        while True:
            shifts, start_simulation_steps = self.work_schedule.get()
            current_time_steps: float = self.env.now + start_simulation_steps
            steps_per_week: int = DateTime.map_time_to_steps(7)
            step_in_week: float = current_time_steps % steps_per_week

            # Determine desired capacity for the current shift
            desired_capacity: int = 0
            next_change: Optional[float] = None
            for shift in shifts:
                if shift[0] <= step_in_week < shift[1]:
                    # If capacity is an int, use it; if a dict, sum the counts
                    cap: Union[int, Dict[str, int]] = shift[2]
                    desired_capacity = cap if isinstance(cap, int) else sum(cap.values())
                    next_change = shift[1] - step_in_week
                    break
            if desired_capacity == 0:
                # Off-shift: desired capacity is zero
                desired_capacity = 0
                differences: List[float] = [shift[0] - step_in_week for shift in shifts if (shift[0] - step_in_week) >= 0]
                if differences:
                    next_change = min(differences)
                else:
                    next_change = steps_per_week - step_in_week + shifts[0][0]

            current_workers_in_store: List[Worker] = list(self.store.items)

            # Calculate how many workers to add or remove
            if len(current_workers_in_store) < desired_capacity:
                workers_to_add: int = min(desired_capacity - len(current_workers_in_store),
                                          len(self.workers) - len(current_workers_in_store))

                store_worker_ids: Set[str] = {w.id for w in current_workers_in_store}
                for worker in self.workers:
                    if worker.id not in store_worker_ids and workers_to_add > 0:
                        self.store.items.append(worker)
                        workers_to_add -= 1

            elif len(current_workers_in_store) > desired_capacity:
                workers_to_remove: int = len(current_workers_in_store) - desired_capacity

                for _ in range(workers_to_remove):
                    if current_workers_in_store:
                        self.store.items.remove(current_workers_in_store.pop())

            # Wait until the next schedule change
            yield self.env.timeout(next_change)


def print_worker_utilization_for_pool(pool_name: str, simulation_time: float) -> None:
    """
    Print a formatted table of worker utilization statistics.

    :param pool_name: Name of the worker pool
    :param simulation_time: Total simulation time
    """
    model: Model = Model()
    pool: Optional[WorkerPool] = model.worker_pools.get(pool_name)
    if pool is not None:
        # Get precision from settings
        precision = cfg.precision

        # Table header
        print(f"\n{'=' * TABLE_WIDTH}")
        print(f"WORKFORCE UTILIZATION ANALYTICS - Pool: '{pool_name}' (Total Time: {simulation_time})")
        print(f"{'-' * TABLE_WIDTH}")

        # Column headers
        format_str: str = "| {:<15} | {:>12} | {:>18} | {:>15} |"
        print(format_str.format("WORKER", "ALLOCATIONS", "TOTAL BUSY TIME", "UTILIZATION (%)"))
        print(f"{'-' * TABLE_WIDTH}")

        # Sort workers by utilization (highest first)
        sorted_workers: List[Worker] = sorted(
            pool.workers,
            key=lambda w: w.total_busy_time,
            reverse=True
        )

        # Worker data
        all_busy_time: float = 0.0
        all_allocations: int = 0

        for worker in sorted_workers:
            utilization: float = (worker.total_busy_time / simulation_time) * 100 if simulation_time > 0 else 0
            print(format_str.format(
                worker.id,
                worker.allocations,
                f"{worker.total_busy_time:.{precision}f}",
                f"{utilization:.{precision}f}%"
            ))

            all_busy_time += worker.total_busy_time
            all_allocations += worker.allocations

        # Summary stats for all workers
        print(f"{'-' * TABLE_WIDTH}")
        avg_utilization: float = (all_busy_time / (simulation_time * len(pool.workers))) * 100 if simulation_time > 0 and pool.workers else 0
        print(format_str.format(
            "AVG PER WORKER",
            "{:.{precision}f}".format(all_allocations / len(pool.workers) if len(pool.workers) > 0 else 0, precision=precision),
            "{:.{precision}f}".format(all_busy_time / len(pool.workers) if len(pool.workers) > 0 else 0, precision=precision),
            "{:.{precision}f}%".format(avg_utilization, precision=precision)
        ))

        # Grand total stats
        print(format_str.format(
            "POOL TOTAL",
            all_allocations,
            "{:.{precision}f}".format(all_busy_time, precision=precision),
            "{:.{precision}f}%".format(all_busy_time / simulation_time * 100 if simulation_time > 0 else 0, precision=precision)
        ))

        # Calculate overall pool capacity utilization
        max_possible_time: float = simulation_time * len(pool.workers)
        pool_capacity_used: float = (all_busy_time / max_possible_time) * 100 if max_possible_time > 0 else 0
        print(format_str.format(
            "POOL CAPACITY",
            f"{len(pool.workers)} workers",
            f"{all_busy_time:.{precision}f}/{max_possible_time:.{precision}f}",
            f"{pool_capacity_used:.{precision}f}%"
        ))

        print(f"{'=' * TABLE_WIDTH}\n")


def print_all_worker_pools_summary(simulation_time: float) -> None:
    """
    Print a summary of all worker pools in the simulation.

    :param simulation_time: Total simulation time
    """
    model: Model = Model()
    if model.worker_pools:
        # Get precision from settings
        precision = cfg.precision

        print(f"\n{'=' * TABLE_WIDTH}")
        print(f"OVERALL WORKFORCE SUMMARY (Total Time: {simulation_time})")
        print(f"{'-' * TABLE_WIDTH}")

        format_str: str = "| {:<15} | {:>12} | {:>18} | {:>15} |"
        print(format_str.format("POOL", "WORKERS", "TOTAL BUSY TIME", "UTILIZATION (%)"))
        print(f"{'-' * TABLE_WIDTH}")

        total_workers: int = 0
        total_busy_time: float = 0.0

        for pool_name, pool in model.worker_pools.items():
            pool_busy_time: float = sum(worker.total_busy_time for worker in pool.workers)
            pool_utilization: float = (pool_busy_time / (simulation_time * len(pool.workers))) * 100 if simulation_time > 0 and pool.workers else 0

            print(format_str.format(
                pool_name,
                len(pool.workers),
                f"{pool_busy_time:.{precision}f}",
                f"{pool_utilization:.{precision}f}%"
            ))

            total_workers += len(pool.workers)
            total_busy_time += pool_busy_time

        print(f"{'-' * TABLE_WIDTH}")
        overall_utilization: float = (total_busy_time / (simulation_time * total_workers)) * 100 if simulation_time > 0 and total_workers > 0 else 0
        print(format_str.format(
            "ALL POOLS",
            total_workers,
            f"{total_busy_time:.{precision}f}",
            f"{overall_utilization:.{precision}f}%"
        ))

        print(f"{'=' * TABLE_WIDTH}\n")


def load_workers_from_csv(csv_path: str, config: Optional[Dict[str, Any]] = None) -> List[Worker]:
    """
    Load a list of workers from a CSV file.
    Expected CSV columns: id

    :param csv_path: Path to the CSV file
    :param config: Optional pandas configuration for CSV reading
    :return: List of Worker objects created from the CSV data
    """
    if config:
        df: pd.DataFrame = pd.read_csv(csv_path, **config)
    else:
        df: pd.DataFrame = pd.read_csv(csv_path)
    workers: List[Worker] = [Worker(row['id']) for _, row in df.iterrows()]
    return workers
