def fifo_strategy(queue: list):
    storage_event = queue.pop(0)
    return storage_event


def lifo_strategy(queue: list):
    storage_event = queue.pop(-1)
    return storage_event
