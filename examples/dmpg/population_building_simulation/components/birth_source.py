import random
import simpy

from examples.dmpg.population_building_simulation import config
from examples.dmpg.population_building_simulation.components.human_entity import Human
from src.core.components.date_time import DateTime
from src.core.components.source import Source
from src.core.components.model import Model


class BirthSource(Source):

    def __init__(self, env: simpy.Environment, name: str, houses: list, death_sink=None, **kwargs):
        self.houses = houses
        self.death_sink = death_sink
        self._rr = 0
        self._birth_acc = 0.0
        self._death_acc = 0.0
        super().__init__(
            env=env,
            name=name,
            creation_time_distribution_with_parameters=None,
            entity_type="Human",
            entity_class=Human,
            **kwargs,
        )

    def run(self):
#https://statistik.nrw/gesellschaft-und-staat/gebiet-und-bevoelkerung/geburten-und-sterbefaelle/sterblichkeit-nach-altersgruppen-und-geschlecht
        mortality_rate = {
            (0, 9): 0.5,
            (10, 19): 0.2,
            (20, 29): 0.3,
            (30, 39): 0.6,
            (40, 49): 1.7,
            (50, 59): 4.3,
            (60, 69): 12.4,
            (70, 79): 30.6,
            (80, 120): 120.0
        }
        while True:
            humans = Model().get_state("humans")
            for h in humans:
                h.age = float(h.age) + (1.0 / 365.0)

            self._birth_acc += float(config.BIRTHS_PER_DAY)
            births = int(self._birth_acc)
            self._birth_acc -= births

            # ---------- GEBURTEN ----------
            for _ in range(births):
                h = Human(
                    name=f"Human_{self.entities_created_pivot_table}",
                    creation_time=self.env.now,
                )
                h.age = 0.0

                house = self.houses[self._rr % len(self.houses)]
                self._rr += 1

                h.home_name = house.name
                h.workplace_name = None
                house.handle_entity_arrival(h)

                humans.append(h)

                self.entities_created_pivot_table += 1
                self.number_exited_pivot_table += 1

            # ---------- TODE ----------
            target_deaths = round(config.DEATHS_PER_DAY * config.SIMULATION_DAYS)
            rate_adj = target_deaths / config.SIMULATION_DAYS

            self._death_acc += rate_adj
            deaths_today = int(self._death_acc)
            self._death_acc -= deaths_today

            if self.death_sink and deaths_today > 0 and humans:
                pool = list(humans)
                deaths_today = min(deaths_today, len(pool))

                for _ in range(deaths_today):
                    weights = []
                    for h in pool:
                        age = int(h.age)
                        weight = 0.1

                        for (min_age, max_age), rate in mortality_rate.items():
                            if min_age <= age <= max_age:
                                weight = rate
                                break

                        weights.append(weight)

                    victim = random.choices(pool, weights=weights, k=1)[0]
                    Model().record_tally_statistic("death_age", int(victim.age))
                    pool.remove(victim)
                    self.death_sink.handle_entity_arrival(victim)

            # Record statistics
            if births > 0:
                Model().record_tally_statistic(config.STAT_BIRTHS, births)
            if deaths_today > 0:
                Model().record_tally_statistic(config.STAT_DEATHS, deaths_today)

            # ---------- POPULATION UPDATE (births only, deaths handled by DeathSink) ----------
            pop = Model().get_state("population")
            Model().update_state("population", pop + births)
            yield self.env.timeout(DateTime.map_time_to_steps(days=1))