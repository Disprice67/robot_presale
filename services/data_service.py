from core import ExceptionGenerator, Economics, IPartNumberFilter


class DataService:

    def __init__(
            self, part_number_filter: IPartNumberFilter,
            exception_generator: ExceptionGenerator,
            economics: Economics
    ):
        self._part_number_filter = part_number_filter
        self._exception_generator = exception_generator
        self._economics = economics

    def generate_exceptions(self, item: dict, key: str, vendor: str,) -> list:
        return self._exception_generator.generate_exceptions(item, key, vendor)

    def costs_by_category(self, item: dict):
        return self._economics.costs_by_category(item)
