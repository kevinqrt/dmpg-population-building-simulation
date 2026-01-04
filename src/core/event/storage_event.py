from simpy import Environment
from simpy.events import Event, EventCallbacks

from src.core.components.entity import Entity


class StorageEvent(Event):

    def __init__(self, env: Environment, called: Entity = None):
        self.env = env
        self.callbacks: EventCallbacks = []
        self._ok = True
        self.called = called
