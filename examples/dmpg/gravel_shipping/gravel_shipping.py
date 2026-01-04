import logging
from src.core.global_imports import random
from src.core.components.server import Server
from src.core.simulation.simulation import run_simulation


class Truck:
    """
    Truck entity for gravel shipping operations.
    Maintains load state and delivery statistics.
    """
    def __init__(self, name):
        self.name = name
        self.load_amount = 0

        # Statistics
        self.total_cycles = 0
        self.successful_loads = 0
        self.failed_loads = 0
        self.total_load_delivered = 0

    def load(self, amount):
        """Load gravel onto truck."""
        self.load_amount = amount

    def unload(self, successful):
        """Unload truck and update statistics."""
        if successful:
            self.successful_loads += 1
            self.total_load_delivered += self.load_amount
        else:
            self.failed_loads += 1
        self.load_amount = 0
        self.total_cycles += 1

    def __repr__(self):
        if self.load_amount > 0:
            return f"{self.name}({self.load_amount}t)"
        return self.name


class SimulationState:
    """Global state management for the gravel shipping simulation."""
    def __init__(self):
        self.gravel_pool = 2000
        self.gravel_shipped = 0
        self.successful_loadings = 0
        self.successful_loading_sizes = 0
        self.unsuccessful_loadings = 0
        self.unsuccessful_loading_sizes = 0
        self.trucks = []
        self.completion_time = None


def gravel_shipping(env):
    """
    Gravel Shipping Simulation Model.

    Simulates shipping 2000 tons of gravel using a fleet of 5 trucks.
    Trucks cycle through: Loading -> Weighing -> back to Loading

    Process Flow:
    1. Initialize 5 trucks at t=0, all start at Loading
    2. Beladen (Loading, 3 docks): Load 34t/38t/41t (60-180 min)
    3. Drive to Weighing: 30/45/60 min
    4. Wiegen (Weighing, 2 stations): Check load (10 min)
       - If ≤40t: Mark as shipped, drive back to Loading
       - If >40t: Return gravel to pool, drive back to Loading
    5. Drive back to Loading: 120/150/180 min
    6. Repeat until 2000t shipped

    Configuration:
    - 5 trucks
    - 3 loading dock stations
    - 2 weighing stations
    """

    # Load simulation state
    state = SimulationState()

    # Create 5 trucks
    state.trucks = [Truck(f"T{i}") for i in range(5)]

    # ========== HELPER FUNCTIONS ==========

    def log_status():
        """Log current simulation status after events."""
        shipped = state.gravel_shipped
        pool = state.gravel_pool
        pct = (shipped / 2000) * 100
        loading_queue = beladen.queue_length
        weighing_queue = wiegen.queue_length

        logging.info(f"[{env.now:7.1f}] - {shipped}t / {pool}t ({pct:.2f}%) "
                     f"#Trucks Loading: {loading_queue}, #Trucks Weighing: {weighing_queue}")

    # ========== DISTRIBUTION FUNCTIONS ==========

    def loading_time_distribution():
        """Random loading time: 60min (30%), 120min (50%), 180min (20%)."""
        rand = random.random()
        if rand < 0.3:
            return 60
        elif rand < 0.8:
            return 120
        else:
            return 180

    # ========== TRIGGER FUNCTIONS ==========

    def before_loading(server, entity, **kwargs):
        """Check if gravel pool has enough before starting to load."""
        if state.gravel_pool <= 0:
            return False
        return True

    def after_loading(server, entity, **kwargs):
        """After loading completes, load random amount onto truck."""
        truck = entity.truck

        # Random load amounts: 34t (30%), 38t (30%), 41t (40%)
        rand = random.random()
        if rand < 0.3:
            desired_load = 34
        elif rand < 0.6:
            desired_load = 38
        else:
            desired_load = 41

        # Load actual amount from pool (less if pool running low)
        actual_load = min(desired_load, state.gravel_pool)
        truck.load(actual_load)
        state.gravel_pool -= actual_load

        logging.debug(f"[{env.now:7.1f}] {truck.name} loaded with {actual_load}t (pool: {state.gravel_pool}t)")
        log_status()
        return True

    def route_after_loading(server, entity):
        """Custom routing after loading - drive to weighing."""
        # Random drive time to weighing: 30min (50%), 45min (28%), 60min (22%)
        rand = random.random()
        if rand < 0.5:
            travel_time = 30
        elif rand < 0.78:
            travel_time = 45
        else:
            travel_time = 60

        def travel_to_weighing():
            yield env.timeout(travel_time)
            wiegen.handle_entity_arrival(entity)

        env.process(travel_to_weighing())

    def after_weighing(server, entity, **kwargs):
        """After weighing, check load and update statistics."""
        truck = entity.truck
        load = truck.load_amount

        # Check if overweight (>40t)
        if load > 40:
            # FAILED - return gravel to pool
            state.gravel_pool += load
            state.unsuccessful_loadings += 1
            state.unsuccessful_loading_sizes += load
            logging.debug(f"[{env.now:7.1f}] {truck.name} FAILED weighing with {load}t (>40t) - returned to pool")
            truck.unload(successful=False)
        else:
            # SUCCESS - ship gravel
            state.gravel_shipped += load
            state.successful_loadings += 1
            state.successful_loading_sizes += load
            logging.debug(f"[{env.now:7.1f}] {truck.name} PASSED weighing with {load}t (shipped: {state.gravel_shipped}t)")
            truck.unload(successful=True)

        log_status()
        return True

    def route_after_weighing(server, entity):
        """Custom routing after weighing - drive back to loading."""
        # Check if simulation should stop (goal reached)
        if state.gravel_shipped >= 2000:
            if state.completion_time is None:
                state.completion_time = env.now
            logging.debug(f"[{env.now:7.1f}] {entity.truck.name} stopping - goal reached")
            return

        # Random drive time back to loading: 120min (50%), 150min (30%), 180min (20%)
        rand = random.random()
        if rand < 0.5:
            travel_time = 120
        elif rand < 0.8:
            travel_time = 150
        else:
            travel_time = 180

        def return_to_loading():
            yield env.timeout(travel_time)

            # Check again after travel (goal might have been reached during travel)
            if state.gravel_shipped < 2000:
                beladen.handle_entity_arrival(entity)
            elif state.completion_time is None:
                state.completion_time = env.now

        env.process(return_to_loading())

    # ========== COMPONENT DEFINITIONS ==========

    # Loading Station (3 docks)
    beladen = Server(
        env,
        name="Beladen",
        processing_time_distribution_with_parameters=(loading_time_distribution,),
        capacity=3,
        before_processing_trigger=before_loading,
        after_processing_trigger=after_loading,
        routing_expression=(route_after_loading,)
    )

    # Weighing Station (2 stations)
    wiegen = Server(
        env,
        name="Wiegen",
        processing_time_distribution_with_parameters=(lambda: 10,),
        capacity=2,
        after_processing_trigger=after_weighing,
        routing_expression=(route_after_weighing,)
    )

    # ========== INITIALIZE 5 TRUCKS AT T=0 ==========
    from src.core.components.entity import Entity

    for i, truck in enumerate(state.trucks):
        entity = Entity(f"Truck_Entity_{i}", env.now, "Default")
        entity.truck = truck
        logging.debug(f"[{env.now:7.1f}] {truck.name} created")
        beladen.handle_entity_arrival(entity)

    # Initial status
    log_status()

    # Store state reference for statistics
    from src.core.components.model import Model
    Model().simulation_state = state


def main():
    """Run the gravel shipping simulation."""
    # Configure logging: INFO level (also available: DEBUG)
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    print("=" * 80)
    print("GRAVEL SHIPPING SIMULATION")
    print("=" * 80)
    print("Goal: Ship 2000 tons of gravel")
    print("Fleet: 5 trucks")
    print("Resources: 3 loading docks, 2 weighing stations")
    print("Max load: 40 tons per truck")
    print("=" * 80 + "\n")

    # Run simulation with a long duration - will stop when complete
    result = run_simulation(model=gravel_shipping, steps=100000, warm_up=0)

    # Flush all logging output before printing summary
    for handler in logging.root.handlers[:]:
        handler.flush()

    # Print final statistics
    from src.core.components.model import Model
    if hasattr(Model(), 'simulation_state'):
        state = Model().simulation_state

        print("\n" + "=" * 80)
        print("FINAL STATISTICS")
        print("=" * 80)

        # Use actual completion time, not total simulation duration
        sim_time = state.completion_time if state.completion_time else Model().env.now

        print(f"\nGravel shipped           = {state.gravel_shipped} tons")
        if state.gravel_shipped > 0:
            print(f"Mean Time / Gravel Unit  = {sim_time / state.gravel_shipped:.2f} minutes")

        total_loads = state.successful_loadings + state.unsuccessful_loadings
        if total_loads > 0:
            avg_succ = state.successful_loading_sizes / state.successful_loadings if state.successful_loadings > 0 else 0
            avg_fail = state.unsuccessful_loading_sizes / state.unsuccessful_loadings if state.unsuccessful_loadings > 0 else 0

            print(f"\nSuccessful loadings      = {state.successful_loadings} "
                  f"({state.successful_loadings/total_loads*100:.2f}%), mean size {avg_succ:.2f}t")

            print(f"Unsuccessful loadings    = {state.unsuccessful_loadings} "
                  f"({state.unsuccessful_loadings/total_loads*100:.2f}%), mean size {avg_fail:.2f}t")

        print(f"\n{'='*80}")
        print("TRUCK STATISTICS")
        print("=" * 80)

        for truck in state.trucks:
            print(f"{truck.name}: {truck.total_cycles} cycles, "
                  f"{truck.successful_loads} successful, {truck.failed_loads} failed, "
                  f"{truck.total_load_delivered:.0f}t delivered")

        print("=" * 80)

    return result


if __name__ == '__main__':
    main()
