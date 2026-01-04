import unittest
import random
import simpy

from src.core.components.model import Model
from src.core.components.entity import EntityManager
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source


class TestCases(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        EntityManager.env = self.env

    def test_add_state(self):
        Model().add_state('test', ['test1', 'test2'])
        simulation_time = 10000

        self.env.run(until=simulation_time)

        assert len(Model().state_variables['test']) == 2

    def test_get_state(self):
        test_list = ['test1', 'test2']
        Model().add_state('test', test_list)
        result_list = Model().get_state('test')
        simulation_time = 10000

        self.env.run(until=simulation_time)

        assert test_list == result_list

    def test_remove_state(self):
        test_list = ['test1', 'test2']
        Model().add_state('test', test_list)
        Model().remove_state('test')

        assert len(Model().state_variables.values()) == 0 and len(Model().state_variables.keys()) == 0

    def test_update_state(self):
        test_list = ['test1', 'test2']
        test_list2 = ['test3', 'test4']
        Model().add_state('test', test_list)
        Model().update_state('test', test_list2)

        assert Model().get_state('test')[0] == test_list2[0] and Model().get_state('test')[1] == test_list2[1]

    def test_update_state_simulation(self):
        def test_routing_with_state(routing_object, entity):
            state = Model().get_state('test')
            state.append(entity.name)
            Model().update_state('test', state)
            next_server_via = routing_object.connections['TestSink']
            next_server_via.handle_entity_arrival(entity)

        Model().add_state('test', [])
        source = Source(self.env, "TestSource", (random.expovariate, 1 / 6))
        server_1 = Server(self.env, "TestServer1", (random.expovariate, 1 / 6), routing_expression=(test_routing_with_state,))
        sink = Sink(self.env, "TestSink")

        source.connect(server_1)
        server_1.connect(sink)

        simulation_time = 10000

        self.env.run(until=simulation_time)

        # Check that the state got update every time an entity left the server
        assert len(Model().get_state('test')) == sink.number_entered_pivot_table
