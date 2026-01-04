from enum import Enum


class NodeType(Enum):
    STORAGE = 'storage'
    COMBINER = 'combiner'
    SEPARATOR = 'separator'
    SERVER = 'server'
    SOURCE = 'source'
    SINK = 'sink'
    ABSTRACTION = 'abstraction'
