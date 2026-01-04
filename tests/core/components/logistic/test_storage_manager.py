import unittest

import simpy

from src.core.components.entity import Entity, EntityManager
from src.core.event.storage_event import StorageEvent
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.server import Server
from src.core.components.exception import EnviromentException
from src.core.components.logistic.storage_manager_strategy import lifo_strategy


class TestCases(unittest.TestCase):

    def test_add_storage_queue(self):
        StorageManager.add_storage_queue('test')

        assert 'test' in StorageManager.storage_queues and 'test' in StorageManager.waiting_server_pools

    def test_add_storage_pool(self):
        StorageManager._add_storage_pool('test')

        assert 'test' not in StorageManager.storage_queues and 'test' in StorageManager.waiting_server_pools

    def test_pop_from_queue(self):
        event = StorageEvent(simpy.Environment())
        StorageManager.add_storage_queue('test')
        StorageManager.storage_queues['test'].append(event)
        stored_event = StorageManager._pop_from_queue('test')

        assert event == stored_event

    def test_add_to_queue_empty_pool(self):
        event = StorageEvent(simpy.Environment())
        StorageManager.add_storage_queue('test')
        StorageManager.add_to_queue('test', event)

        assert len(StorageManager.storage_queues['test']) == 1

    def test_remove_from_pool(self):
        env = simpy.Environment()
        dummy_server = Server(env, 'dummy Server')
        StorageManager.add_storage_queue('test')
        StorageManager.waiting_server_pools['test'].append(dummy_server)
        StorageManager.remove_from_pool('test', dummy_server)

        assert len(StorageManager.waiting_server_pools['test']) == 0

    def test_release_next_entity_empty_queue(self):
        env = simpy.Environment()
        dummy_server = Server(env, 'dummy Server')
        StorageManager.add_storage_queue('test')
        StorageManager.release_next_entity('test', dummy_server)

    def test_release_next_entity(self):
        env = simpy.Environment()
        dummy_server = Server(env, 'dummy Server')
        EntityManager.initialize(env)
        event = StorageEvent(env, Entity('dummy', 0))
        StorageManager.env = env
        StorageManager.add_storage_queue('test')
        StorageManager.add_to_queue('test', event)
        StorageManager.release_next_entity('test', (dummy_server, False))

        assert len(StorageManager.storage_queues['test']) == 0

    def test_release_next_entity_error(self):
        with self.assertRaises(EnviromentException):
            env = simpy.Environment()
            dummy_server = Server(env, 'dummy Server')
            EntityManager.initialize(env)
            event = StorageEvent(env, Entity('dummy', 0))
            StorageManager.env = None
            StorageManager.add_storage_queue('test')
            StorageManager.add_to_queue('test', event)
            StorageManager.release_next_entity('test', (dummy_server, False))

    def test_reset(self):
        StorageManager.add_storage_queue('test')
        StorageManager.reset()

        assert len(StorageManager.storage_queues) == 0 and len(StorageManager.waiting_server_pools) == 0

    def test_custom_strategy(self):
        StorageManager.add_storage_queue('test', (lifo_strategy,))
