from enum import Enum


class ComponentType(Enum):
    """
    Enumeration for different types of components in the simulation model.
    """
    SOURCES = 'Sources'
    SERVERS = 'Servers'
    SINKS = 'Sinks'
    VEHICLES = 'Vehicles'
    COMBINER = 'Combiner'
    SEPARATORS = 'Separators'
    STORAGE = 'Storage'
    CONNECTIONS = 'Connections'
