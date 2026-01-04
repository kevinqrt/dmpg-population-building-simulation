from simpy import Event, Environment
from simpy.events import EventCallbacks


class TransportRequestEvent(Event):
    """
    Event that gets triggered when an entity, from class warentraeger, waits for transportation.
    """
    def __init__(
        self,
        env: Environment,
        entity,
        destination,
        location,
    ):
        self.env = env
        self.callbacks: EventCallbacks = []
        self._ok = True
        self.transporter = None
        self.entity = entity
        self.destination = destination
        self.location = location
