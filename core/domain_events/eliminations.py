from core.interfaces.i_logger import IRobotLogger


class EliminationFilter:
    def __init__(self, robot_logger: IRobotLogger):
        self._robot_logger = robot_logger

    @staticmethod
    def filter(key: str) -> str:
        """Filters a given key by removing non-alphanumeric characters and converting to uppercase."""
        getvals = [val for val in str(key) if val.isalpha() or val.isnumeric()]
        return "".join(getvals).upper()
