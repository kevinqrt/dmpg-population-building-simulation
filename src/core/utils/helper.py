from typing import Tuple, Callable, Union
import src.core.config as cfg

ROUND_DECIMAL_PLACES = 4


def get_value_from_distribution_with_parameters(dwp: Tuple[Callable[..., float]]):
    """
    Get a value from a distribution with parameters.

    :param dwp: Tuple of distribution function and parameters

    :return: Value from the distribution
    """
    distribution, parameters = dwp[0], dwp[1:]
    return distribution(*parameters)


def validate_probabilities(component):
    """
    Validate that the total routing probability for a component sums to 100 or 0.

    :param component: The component to validate
    """
    total_probability = sum(connection.probability for connection, _ in component.connection_cache.values() if connection.probability is not None)
    if total_probability != 100 and total_probability != 0:
        raise ValueError(f"Total routing probability for {component} must sum to 100, but got {total_probability}")


def validate_entity_weights(source, entity_with_weigths):
    """
    Validate that the weight of an entity matches the weight of an entity.

    :param source: Name of the source that is checked
    :param entity_with_weigths: Dictonary with the entity and its weights
    """
    total_weight = sum(weight for weight in entity_with_weigths.values() if weight is not None)
    if total_weight != 1:
        raise ValueError(f'Total entity weights must sum to 1, but got {total_weight} for {source}')


def create_connection_cache(component):
    """
    Create and update the connection cache for a component based on its next components and probabilities.

    :param component: The component to update the connection cache for
    """
    component.connection_cache.clear()  # Clear existing cache to avoid stale entries
    total_probability = sum(probability for _, probability, _, _ in component.next_components if probability is not None)

    if total_probability == 0:
        num_components = len(component.next_components)
        equal_probability = 100 / num_components if num_components > 0 else 0
        cumulative_probability = 0
        for next_server, _, entity_type, vehicle in component.next_components:
            cumulative_probability += equal_probability
            component.connection_cache[cumulative_probability] = (component.connections[next_server.name], vehicle)
    else:
        cumulative_probability = 0
        for next_server, probability, entity_type, vehicle in component.next_components:
            if probability is not None and probability != 0:
                cumulative_probability += (probability / total_probability) * 100
                component.connection_cache[cumulative_probability] = (component.connections[next_server.name], vehicle)


def round_value(val: Union[int, float]):
    """
    Rounds a given value to a predefined number of decimal places.

    :param val: The value to be rounded
    :return: The rounded value as either int or float
    """
    # Get precision from settings
    return round(val, cfg.precision) if isinstance(val, float) else val


def count_entity_type(entity_type: str, queue: list):
    """
    Counts the number of an entity type in the queue.

    :param entity_type: Type of the entity to count.
    :param queue: The queue where the entites are in.
    :return: Number of appearences of an entity type.
    """

    return sum(1 for entity in queue if entity[0].entity_type == entity_type)


def get_entity_by_type(entity_type: str, queue: list):
    """
    Gets the first entity of a specific type from a queue.

   :param entity_type: Type of the entity to count.
   :param queue: The queue where the entites are in.
   :return: First entity of the entity type in the queue.
   """
    found_index = None
    found_entity = None
    i = 0

    while found_entity is None:
        if queue[i][0].entity_type == entity_type:
            found_index = i
            found_entity = queue[i]
        i += 1

    if found_index is not None:
        del queue[found_index]
        return found_entity


def execute_trigger(trigger, component, entity, *args, **kwargs) -> bool:
    """
    Execute a trigger function if it exists.

    :param trigger: The trigger function to execute
    :param component: The component that triggered the callback
    :param entity: The entity being processed (can be None for pre-creation triggers)
    :param args: Additional positional arguments
    :param kwargs: Additional keyword arguments
    :return: Result of the trigger function (True by default) or False if execution should be aborted
    """
    if trigger is None:
        return True

    try:
        if isinstance(trigger, tuple):
            # If trigger is a tuple, first element is the function, rest are additional args
            func, *additional_args = trigger
            result = func(component, entity, *(additional_args + list(args)), **kwargs)
        else:
            # If trigger is just a function
            result = trigger(component, entity, *args, **kwargs)

        # If the trigger returns None, treat it as True (continue processing)
        return True if result is None else bool(result)
    except Exception as e:
        # Log exception but don't crash the simulation
        import logging
        logging.error(f"Error executing trigger in {component.name}: {str(e)}")
        return True  # Allow processing to continue despite the trigger error
