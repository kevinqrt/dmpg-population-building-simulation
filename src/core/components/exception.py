

class FreeCapacityException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class DestionationException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class EnviromentException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class MissingVehicleException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
