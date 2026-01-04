from src.core.utils.utils import get_upper_and_lower_bound


def get_vehicle_with_lowest_queue(vehicle_group: list, calling_object, entity, destination):
    vehicle_with_lowest_queue = None
    for vehicle in vehicle_group:
        if vehicle_with_lowest_queue is None:
            vehicle_with_lowest_queue = vehicle

        if len(vehicle.entity_queue) < len(vehicle_with_lowest_queue.entity_queue):
            vehicle_with_lowest_queue = vehicle

    return vehicle_with_lowest_queue


def get_vehicle_with_no_collusion(vehicle_group: list, calling_object, entity, destination):
    optimal_vehicle = None

    for vehicle_a in vehicle_group:
        if vehicle_a.idle:
            vehicle = vehicle_a
            if optimal_vehicle is None:
                optimal_vehicle = vehicle
            for vehicle_b in vehicle_group:
                if vehicle_a != vehicle_b:
                    lower_bound_vehicle_a, upper_bound_vehicle_a = get_upper_and_lower_bound(vehicle_a, calling_object, destination, True)
                    lower_bound_vehicle_b, upper_bound_vehicle_b = get_upper_and_lower_bound(vehicle_b, calling_object, destination, False)

                    if lower_bound_vehicle_b <= upper_bound_vehicle_a <= upper_bound_vehicle_b:
                        # colusion found
                        vehicle = None
                        break
                    if lower_bound_vehicle_b <= lower_bound_vehicle_a <= upper_bound_vehicle_b:
                        # colusion found
                        vehicle = None
                        break
            if vehicle:
                distance_a = abs(vehicle.position[1] - destination.position[1])
                distance_b = abs(optimal_vehicle.position[1] - destination.position[0])
                if distance_a < distance_b:
                    optimal_vehicle = vehicle

    return optimal_vehicle
