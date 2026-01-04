from src.core.components.work_schedule import WorkScheduleDay, WorkScheduleWeek
from src.core.components.date_time import DateTime
from src.core.components.entity import Entity
from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_replications
from src.core.components.model import Model


class SubEntity(Entity):

    tally_statistic = "num_times_processed"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        setattr(self, SubEntity.tally_statistic, 0)


def increase_number_times_processed(server, entity, *args, **kwargs):
    setattr(entity, SubEntity.tally_statistic, getattr(entity, SubEntity.tally_statistic) + 1)


def record_num_times_processed(server, entity, *args, **kwargs):
    Model().record_tally_statistic(SubEntity.tally_statistic, entity.num_times_processed)


def setup_model5_2(env):

    Model().add_tally_statistic(SubEntity.tally_statistic)

    inspection_workday = WorkScheduleDay()
    inspection_workday.set_time(0, 0, 4, 0)
    inspection_workday.set_time(5, 0, 12, 0)
    inspection_workday.set_time(13, 0, 20, 0)
    inspection_workday.set_time(21, 0, 24, 0)

    inspection_week = WorkScheduleWeek(inspection_workday, inspection_workday, inspection_workday, inspection_workday,
                                       inspection_workday, inspection_workday, inspection_workday)
    # inspection_week.print_stats("inspection_week")

    rework_workday = WorkScheduleDay()
    rework_workday.set_time(16, 0, 20, 0)
    rework_workday.set_time(21, 0, 24, 0)
    rework_workday.set_time(0, 0, 1, 0)

    rework_week = WorkScheduleWeek(rework_workday, rework_workday, rework_workday, rework_workday,
                                   rework_workday, rework_workday, rework_workday)

    source = Source(env, "PCB", (random.expovariate, 1 / 6), entity_class=SubEntity)
    placement = Server(env, "Placement", (random.triangular, 3, 5, 4),
                       after_processing_trigger=increase_number_times_processed,
                       time_between_machine_breakdowns=(random.expovariate, 1 / 360),    # breakdown after 6 hours
                       machine_breakdown_duration=(random.expovariate, 1 / 30))          # breakdown 30 minutes
    inspection = Server(env, "Inspection", (random.uniform, 2, 4),
                        work_schedule=inspection_week)
    rework = Server(env, "Rework", (random.triangular, 2, 6, 4),
                    work_schedule=rework_week)

    goodparts = Sink(env, "GoodParts", before_processing_trigger=record_num_times_processed)
    badparts = Sink(env, "BadParts", before_processing_trigger=record_num_times_processed)

    # Set up connections with routing probabilities for servers
    source.connect(placement)

    placement.connect(inspection)
    rework.connect(placement)

    inspection.connect(goodparts, 66)       # 66% probability to route to GoodParts
    inspection.connect(badparts, 8)         # 8% probability to route to BadParts
    inspection.connect(rework, 26)          # 26% probability to route to Rework


def main():
    run_replications(model=setup_model5_2, steps=DateTime.map_time_to_steps(days=125),
                     warm_up=DateTime.map_time_to_steps(days=25), num_replications=25, multiprocessing=True)


if __name__ == '__main__':
    main()
