from core.entities.validate_data import InputData
from pathlib import Path
from typing import Protocol, Optional


# HandlerInterface
class IMonitorFiles(Protocol):
    def start_monitoring(self, directory_paths: list[str]):
        ...


class IExcelHandler(Protocol):
    @property
    def _sample_file(self,):
        ...

    def read_excel(self, file_path: Path) -> Optional[list[InputData]]:
        ...

    def write_to_excel(self, data: dict, file_path: Path):
        ...

    def get_output_file(self, filename: str):
        ...


class ISYSHandler(Protocol):
    def start_monitoring(self):
        ...
