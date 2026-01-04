import time
import simpy
import sys
import os

from examples.dmpg.population_building_simulation.components.human_entity import Human

# Setze den Pfad zum Projektstammverzeichnis, z.B. zum ModSim-Projekt
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Füge den Projektstammpfad zum sys.path hinzu
sys.path.insert(0, project_root)

def generate_population(n, env):
    humans = []
    for i in range(n):
        name = f"Person_{i}"
        creation_time = env.now
        humans.append(Human(name=name, creation_time=creation_time))
    return humans

def performance_test():
    # Erstelle die Simulationsumgebung
    env = simpy.Environment()

    # Initialisiere den EntityManager mit der Umgebung
    from src.core.components.entity import EntityManager
    EntityManager.initialize(env)

    sizes = [6000, 60000, 600000, 6000000]

    print(f"{'Anzahl':>10} | {'Dauer (Sekunden)':>20} | {'Dauer (Millisekunden)':>25}")
    print("-" * 60)

    for size in sizes:
        start_time = time.time()
        population = generate_population(size, env)
        end_time = time.time()
        duration = end_time - start_time
        duration_ms = duration * 1000

        print(f"{size:>10} | {duration:>20.2f} | {duration_ms:>25.2f}")

if __name__ == "__main__":
    performance_test()

