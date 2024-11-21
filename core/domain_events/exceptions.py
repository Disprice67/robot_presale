from typing import Protocol
from core.interfaces.i_logger import IRobotLogger


class IParsing(Protocol):
    def get_part_and_model(self, key: str) -> list[str]:
        ...


class ExceptionGenerator:
    def __init__(self, parsing_instance: IParsing, robot_logger: IRobotLogger, exception: dict = None):
        self._robot_logger = robot_logger
        self.parsing_instance = parsing_instance
        self.exception = exception or {
            '24': '48',
            '48': '24',
            'K7': ('K8', 'K9'),
            'K8': ('K7', 'K9'),
            'K9': ('K7', 'K8')
        }

    def _replace_key(self, part_num: str) -> list[str]:
        """Helper function to replace part of the part number based on the exception rules."""
        result = [part_num]
        for exc, repl in self.exception.items():
            if exc in part_num:
                repl_values = repl if isinstance(repl, tuple) else (repl,)
                result.extend(part_num.replace(exc, r) for r in repl_values)
        return result

    def generate_exceptions(self, key: str, vendor: str) -> list[str]:
        """Generate exception part numbers based on the provided key and vendor."""
        item = []

        if vendor == 'HUAWEI':
            pars = self.parsing_instance.get_part_and_model(key)
            if pars:
                item.extend(pars)
        elif vendor == 'CISCO' and 'R-' in key:
            item.append(key.replace('R-', ''))

        item.extend(self._replace_key(key))
        return item
