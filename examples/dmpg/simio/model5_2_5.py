from src.core.components.date_time import DateTime
from src.core.components.work_schedule import WorkScheduleDay, WorkScheduleWeek
from src.core.components.model import Model
from src.core.global_imports import random
from src.core.components.entity import Entity
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_replications

MAX_PROCESSING_COUNT = 10


class SubEntity(Entity):

    tally_statistic = "num_times_processed"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.reset()

        sequence_index = kwargs.get('sequence_index')
        if sequence_index is not None:
            self.sequence_index = sequence_index

    def __repr__(self):
        return f"{self.name} ({self.creation_time})" if not self.destruction_time \
            else f"{self.name} ({self.destruction_time - self.creation_time})"

    def reset(self):
        setattr(self, SubEntity.tally_statistic, 0)


def after_processing_trigger(server, entity, *args, **kwargs):
    """
    Increment processing count after entity is processed.
    """
    setattr(entity, SubEntity.tally_statistic, getattr(entity, SubEntity.tally_statistic) + 1)
    return True


def before_entity_destruction_trigger(sink, entity, *args, **kwargs):
    """
    Record tally statistic before entity is destroyed.
    """
    Model().record_tally_statistic(SubEntity.tally_statistic, entity.num_times_processed)
    return True


def change_routing_trigger(server, entity, *args, **kwargs):
    """
    Route entities that exceed processing limit to BadParts sink.
    """
    # For entities over limit, route to BadParts
    if isinstance(entity, SubEntity) and getattr(entity, SubEntity.tally_statistic) >= MAX_PROCESSING_COUNT:
        for next_component, *_ in server.next_components:
            if next_component.name == "BadParts":
                next_component.handle_entity_arrival(entity)
                server.number_exited_pivot_table += 1
                return False
    return True


def change_routing_to_2nd_placement_trigger(server, entity, *args, **kwargs):
    """
    Route entities to the placement server with the shortest queue.
    """
    after_processing_trigger(server, entity, *args, **kwargs)
    if isinstance(entity, SubEntity):
        # find component with minimal queue length
        minimal_queue_length_component = None

        for next_component, *_ in server.next_components:
            if minimal_queue_length_component is None:
                minimal_queue_length_component = next_component
                continue

            if next_component.queue_length < minimal_queue_length_component.queue_length:
                minimal_queue_length_component = next_component

        minimal_queue_length_component.handle_entity_arrival(entity)
        server.number_exited_pivot_table += 1
        return False

    return True


def setup_model5_2(env):
    Model().add_tally_statistic(SubEntity.tally_statistic)

    inspection_workday = WorkScheduleDay()
    inspection_workday.set_time(0, 0, 4, 0)
    inspection_workday.set_time(5, 0, 12, 0)
    inspection_workday.set_time(13, 0, 20, 0)
    inspection_workday.set_time(21, 0, 24, 0)

    inspection_week = WorkScheduleWeek(inspection_workday, inspection_workday, inspection_workday, inspection_workday,
                                       inspection_workday, inspection_workday, inspection_workday)

    rework_workday = WorkScheduleDay()
    rework_workday.set_time(16, 0, 20, 0)
    rework_workday.set_time(21, 0, 24, 0)
    rework_workday.set_time(0, 0, 1, 0)

    rework_week = WorkScheduleWeek(rework_workday, rework_workday, rework_workday, rework_workday,
                                   rework_workday, rework_workday, rework_workday)

    source = Source(env, "PCB", (random.expovariate, 1 / 6), entity_class=SubEntity)

    placement = Server(env, "Placement", (random.triangular, 3, 5, 4),
                       after_processing_trigger=change_routing_to_2nd_placement_trigger)

    fine_pitch_fast = Server(env, "FinePitchFast", (random.triangular, 8, 10, 9),
                             after_processing_trigger=after_processing_trigger,
                             time_between_machine_breakdowns=(random.expovariate, 1 / 360),
                             machine_breakdown_duration=(random.expovariate, 1 / 30))
    fine_pitch_medium = Server(env, "FinePitchMedium", (random.triangular, 10, 14, 12),
                               after_processing_trigger=after_processing_trigger)
    fine_pitch_slow = Server(env, "FinePitchSlow", (random.triangular, 12, 16, 14),
                             after_processing_trigger=after_processing_trigger)

    inspection = Server(env, "Inspection", (random.uniform, 2, 4),
                        after_processing_trigger=change_routing_trigger, work_schedule=inspection_week)

    rework = Server(env, "Rework", (random.triangular, 2, 6, 4),
                    work_schedule=rework_week)

    # Sinks with before_processing_trigger to record processing count
    good_parts = Sink(env, "GoodParts", before_processing_trigger=before_entity_destruction_trigger)
    bad_parts = Sink(env, "BadParts", before_processing_trigger=before_entity_destruction_trigger)

    # Set up connections with routing probabilities for servers
    source.connect(placement)

    placement.connect(fine_pitch_fast)
    placement.connect(fine_pitch_medium)
    placement.connect(fine_pitch_slow)

    fine_pitch_fast.connect(inspection)
    fine_pitch_medium.connect(inspection)
    fine_pitch_slow.connect(inspection)
    rework.connect(placement)

    inspection.connect(good_parts, 66)
    inspection.connect(bad_parts, 8)
    inspection.connect(rework, 26)


def main():
    run_replications(model=setup_model5_2, steps=DateTime.map_time_to_steps(days=125),
                     warm_up=DateTime.map_time_to_steps(days=25), num_replications=25, multiprocessing=True)


if __name__ == '__main__':
    main()
