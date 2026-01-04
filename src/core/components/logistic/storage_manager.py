import logging
from collections import deque
from typing import Tuple

from src.core.components.date_time import DateTime
from src.core.components.exception import EnviromentException
from src.core.components.logistic.storage_manager_strategy import fifo_strategy
from src.core.components_abstract.singleton import Singleton
from src.core.event.storage_event import StorageEvent
from src.core.global_imports import ENTITY_PROCESSING_LOG_ENTRY


class StorageManager(Singleton):
    """The storage manager handles all storage queues and pools. If a queue is empty and a server requests
    a new entity, the server will be placed in the pool of the queue. The next time an entity is added to the
    storage queue, it will instead be released and send to the first server in the pool of the queue."""

    # Manages the waiting entites
    storage_queues = {}
    # Manages the strategy for the different queues
    storage_queue_strategy = {}
    # Manages the waiting server for the arrival of an entity
    waiting_server_pools = {}

    env = None

    @classmethod
    def add_storage_queue(cls, queue: str, strategy: Tuple = None):
        if strategy is not None:
            cls.storage_queue_strategy[queue] = strategy
        else:
            cls.storage_queue_strategy[queue] = (fifo_strategy,)

        cls.storage_queues[queue] = []
        cls._add_storage_pool(queue)

    @classmethod
    def _add_storage_pool(cls, queue: str):
        cls.waiting_server_pools[queue] = deque()

    @classmethod
    def _pop_from_queue(cls, queue: str, param: dict | None = None) -> StorageEvent:
        storage_event = None
        if param is None:
            param = {}
        if len(cls.storage_queues[queue]) > 0:
            storage_event = cls.storage_queue_strategy[queue][0](cls.storage_queues[queue], **param)
        return storage_event

    @classmethod
    def add_to_queue(cls, queue: str, storage_event: StorageEvent):
        cls.storage_queues[queue].append(storage_event)

        logging.root.level <= logging.TRACE and logging.trace(
            ENTITY_PROCESSING_LOG_ENTRY.format(f"{storage_event.called.name} add to {queue}, Queue size: {len(cls.storage_queues[queue])}",
                                               DateTime.get(cls.env.now)))

        # Get number of waiting servers before the loop
        num_waiting = len(cls.waiting_server_pools[queue])

        for _ in range(num_waiting):
            server, multipool = cls.waiting_server_pools[queue].popleft()
            if multipool:
                cls._remove_from_all_pools(server)
            server.get_next_entity_from_queue()

    @classmethod
    def release_next_entity(cls, queue: str, server, param: dict = None) -> bool:
        storage_event = cls._pop_from_queue(queue, param)
        if storage_event is None:
            if server not in cls.waiting_server_pools[queue]:
                cls.waiting_server_pools[queue].append(server)
        else:
            if cls.env is not None:
                storage_event.called.destination = server[0]
                cls.env.schedule(storage_event)
            else:
                raise EnviromentException('Enviroment is not set!')

    @classmethod
    def remove_from_pool(cls, queue: str, server):
        if server in cls.waiting_server_pools[queue]:
            cls.waiting_server_pools[queue].remove(server)

    @classmethod
    def reset(cls):
        cls.storage_queues = {}
        cls.waiting_server_pools = {}
        cls.env = None

    @classmethod
    def is_queue_empty(cls, queue: str):
        if len(cls.storage_queues[queue]) == 0:
            return True
        else:
            return False

    @classmethod
    def _remove_from_all_pools(cls, server):
        for pool in cls.waiting_server_pools:
            if server in cls.waiting_server_pools[pool]:
                cls.waiting_server_pools[pool].remove(server)
