from src.core.components.entity import Entity

# Source
NUMBER_CREATED = "NumberCreated"
NUMBER_EXITED = "NumberExited"

# Sink
AVG_TIME_IN_SYSTEM = "TimeInSystem (average)"
MAX_TIME_IN_SYSTEM = "TimeInSystem (max)"
MIN_TIME_IN_SYSTEM = "TimeInSystem (min)"
TOTAL_TIME_IN_SYSTEM = "TimeInSystem (total)"
NUMBER_ENTERED = "NumberEntered"

# Server
AVG_ENTITES_IN_QUEUE = "EntitiesInQueue (average)"
MAX_ENTITES_IN_QUEUE = "EntitiesInQueue (max)"
TOTAL_ENTITES_IN_QUEUE = "EntitiesInQueue (total)"
AVG_TIME_IN_QUEUE = "TimeInQueue (average)"
MAX_TIME_IN_QUEUE = "TimeInQueue (max)"
AVG_TIME_PROCESSING = "TimeProcessing (average)"
TOTAL_TIME_PROCESSING = "TimeProcessing (total)"
QUEUE_LENGTH = "queue_length"
QUEUE_LENGTHS = "queue_lengths"
QUEUE_TIMES = "queue_times"
ENTITIES_PROCESSED = "EntitiesProcessed"

# Combiner
MEMBERS_QUEUE_LENGTH = "members_queue_length"
MEMBERS_QUEUE_LENGTHS = "members_queue_lengths"
MEMBERS_QUEUE_TIMES = "members_queue_times"
PARENTS_QUEUE_LENGTH = "parents_queue_length"
PARENTS_QUEUE_LENGTHS = "parents_queue_lengths"
PARENTS_QUEUE_TIMES = "parents_queue_times"
ENTITIES_IN_QUEUE_TOTAL = "EntitiesInQueue (total)"
MEMBERS_ENTERED = "MembersEntered"
MEMBERS_IN_QUEUE_AVG = "MembersInQueue (average)"
MEMBERS_IN_QUEUE_MAX = "MembersInQueue (max)"
MEMBERS_TIME_IN_QUEUE_AVG = "Members TimeInQueue (average)"
MEMBERS_TIME_IN_QUEUE_MAX = "Members TimeInQueue (max)"
PARENTS_ENTERED = "ParentsEntered"
PARENTS_IN_QUEUE_AVG = "ParentsInQueue (average)"
PARENTS_IN_QUEUE_MAX = "ParentsInQueue (max)"
PARENTS_TIME_IN_QUEUE_AVG = "Parents TimeInQueue (average)"
PARENTS_TIME_IN_QUEUE_MAX = "Parents TimeInQueue (max)"
TIME_PROCESSING_AVG = "TimeProcessing (average)"
TIME_PROCESSING_TOTAL = "TimeProcessing (total)"


def initialize_entity_types_source(entity_type_stats: dict, entity: Entity) -> None:
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            NUMBER_CREATED: 0,
            NUMBER_EXITED: 0
        }


def initialize_entity_types_sink(entity_type_stats: dict, entity: Entity):
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            AVG_TIME_IN_SYSTEM: 0,
            MAX_TIME_IN_SYSTEM: 0,
            MIN_TIME_IN_SYSTEM: float('inf'),
            NUMBER_ENTERED: 0,
            "NumTimesProcessed (average)": 0,
            "NumTimesProcessed (max)": 0,
            "NumTimesProcessed (min)": 0,
            TOTAL_TIME_IN_SYSTEM: 0.0
        }
    else:
        entity_type_stats[entity.entity_type][AVG_TIME_IN_SYSTEM] = 0
        entity_type_stats[entity.entity_type][MAX_TIME_IN_SYSTEM] = 0
        entity_type_stats[entity.entity_type][MIN_TIME_IN_SYSTEM] = 0
        entity_type_stats[entity.entity_type][TOTAL_TIME_IN_SYSTEM] = 0
        entity_type_stats[entity.entity_type][NUMBER_ENTERED] = 0
        entity_type_stats[entity.entity_type]["NumTimesProcessed (average)"] = 0
        entity_type_stats[entity.entity_type]["NumTimesProcessed (max)"] = 0
        entity_type_stats[entity.entity_type]["NumTimesProcessed (min)"] = 0


def update_entity_types_sink(entity_type_stats: dict, entity: Entity, time_in_system):
    stats = entity_type_stats[entity.entity_type]
    try:
        stats[TOTAL_TIME_IN_SYSTEM] += time_in_system
    except KeyError:
        pass
    stats[MAX_TIME_IN_SYSTEM] = max(stats[MAX_TIME_IN_SYSTEM], time_in_system)
    stats[MIN_TIME_IN_SYSTEM] = min(stats[MIN_TIME_IN_SYSTEM], time_in_system)
    stats[NUMBER_ENTERED] += 1
    stats[AVG_TIME_IN_SYSTEM] = stats[TOTAL_TIME_IN_SYSTEM] / stats[NUMBER_ENTERED]


def initialize_entity_types_component(entity_type_stats: dict, entity: Entity):
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            TOTAL_ENTITES_IN_QUEUE: 0,
            ENTITIES_PROCESSED: 0,
            AVG_ENTITES_IN_QUEUE: 0,
            MAX_ENTITES_IN_QUEUE: 0,
            AVG_TIME_IN_QUEUE: 0,
            MAX_TIME_IN_QUEUE: 0,
            AVG_TIME_PROCESSING: 0,
            TOTAL_TIME_PROCESSING: 0,
            QUEUE_LENGTH: 0,
            QUEUE_LENGTHS: [],
            QUEUE_TIMES: []
        }


def initialize_entity_types_vehicle(entity_type_stats: dict, entity: Entity):
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            TOTAL_ENTITES_IN_QUEUE: 0,
            AVG_ENTITES_IN_QUEUE: 0,
            MAX_ENTITES_IN_QUEUE: 0,
            AVG_TIME_IN_QUEUE: 0,
            MAX_TIME_IN_QUEUE: 0,
            QUEUE_LENGTH: 0,
            QUEUE_LENGTHS: [],
            QUEUE_TIMES: [],
            "EntitiesTransported": 0,
            "TotalTrips": 0,
            "TravelTime (total)": 0.0,
            "TravelTime (average)": 0
        }


def initialize_entity_types_storage(entity_type_stats: dict, entity: Entity):
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            TOTAL_ENTITES_IN_QUEUE: 0,
            ENTITIES_PROCESSED: 0,
            AVG_ENTITES_IN_QUEUE: 0,
            MAX_ENTITES_IN_QUEUE: 0,
            AVG_TIME_IN_QUEUE: 0,
            MAX_TIME_IN_QUEUE: 0,
            AVG_TIME_PROCESSING: 0,
            TOTAL_TIME_PROCESSING: 0,
            QUEUE_LENGTH: 0,
            QUEUE_LENGTHS: [],
            QUEUE_TIMES: []
        }


def initialize_entity_types_separator(entity_type_stats: dict, entity: Entity):
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            TOTAL_ENTITES_IN_QUEUE: 1,
            ENTITIES_PROCESSED: 2,
            AVG_ENTITES_IN_QUEUE: 0,
            MAX_ENTITES_IN_QUEUE: 0,
            AVG_TIME_IN_QUEUE: 0,
            MAX_TIME_IN_QUEUE: 0,
            AVG_TIME_PROCESSING: 0,
            TOTAL_TIME_PROCESSING: 0,
            QUEUE_LENGTH: 0,
            QUEUE_LENGTHS: [],
            QUEUE_TIMES: []
        }


def initialize_entity_types_combiner(entity_type_stats: dict, entity: Entity):
    if entity.entity_type not in entity_type_stats:
        entity_type_stats[entity.entity_type] = {
            ENTITIES_IN_QUEUE_TOTAL: 0,
            ENTITIES_PROCESSED: 0,
            MEMBERS_ENTERED: 0,
            MEMBERS_IN_QUEUE_AVG: 0,
            MEMBERS_IN_QUEUE_MAX: 0,
            MEMBERS_TIME_IN_QUEUE_AVG: 0,
            MEMBERS_TIME_IN_QUEUE_MAX: 0,
            PARENTS_ENTERED: 0,
            PARENTS_IN_QUEUE_AVG: 0,
            PARENTS_IN_QUEUE_MAX: 0,
            PARENTS_TIME_IN_QUEUE_AVG: 0,
            PARENTS_TIME_IN_QUEUE_MAX: 0,
            TIME_PROCESSING_AVG: 0,
            TIME_PROCESSING_TOTAL: 0,
            MEMBERS_QUEUE_TIMES: [],
            MEMBERS_QUEUE_LENGTHS: [],
            MEMBERS_QUEUE_LENGTH: 0,
            PARENTS_QUEUE_LENGTH: 0,
            PARENTS_QUEUE_TIMES: [],
            PARENTS_QUEUE_LENGTHS: []
        }
