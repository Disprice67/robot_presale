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

    def generate_exceptions(self, item: dict, key: str, vendor: str) -> list[str]:
        """Generate exception part numbers based on the provided key and vendor."""
        part_numbers = []

        if vendor.upper() == 'HUAWEI':
            pars = self.parsing_instance.get_part_and_model(key)
            if pars:
                item['MODEL/PN'] = ', '.join(pars)
        elif vendor.upper() == 'CISCO' and 'R-' in key:
            part_numbers.append(key.replace('R-', ''))

        if item.get('MODEL/PN'):
            replaces_list = []
            for pn in pars:
                replaces_list.extend(self._replace_key(pn))
            part_numbers.extend(replaces_list)
        else:
            part_numbers.extend(self._replace_key(key))
        return part_numbers
