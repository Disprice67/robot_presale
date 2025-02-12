from core import EliminationFilter, ExceptionGenerator, IParsing, Economics


class DataService:

    def __init__(
            self, elimination_filter: EliminationFilter,
            exception_generator: ExceptionGenerator,
            economics: Economics
    ):
        self._elimination_filter = elimination_filter
        self._exception_generator = exception_generator
        self._economics = economics

    def elimination(self,):
        return self._elimination_filter

    def generate_exceptions(self, item: dict, key: str, vendor: str,) -> list:
        return self._exception_generator.generate_exceptions(item, key, vendor)

    def costs_by_category(self, item: dict):
        return self._economics.costs_by_category(item)
