from core.interfaces.i_handler import IMonitorFiles, IExcelHandler, ISYSHandler
from core.entities.validate_data import InputData
from pathlib import Path
from typing import Optional


class MonitorFilesService:
    def __init__(self, monitor_files: IMonitorFiles):
        self.monitor_files = monitor_files

    def start_monitoring(self, directory_paths: list[str]):
        return self.monitor_files.start_monitoring(directory_paths)


class ExcelHandlerService:
    def __init__(self, excel_handler: IExcelHandler):
        self.excel_handler = excel_handler

    def get_output_file(self, filename: str):
        return self.excel_handler.get_output_file(filename)

    def read_excel(self, filedir: Path) -> Optional[list[InputData]]:
        return self.excel_handler.read_excel(filedir)

    def write_to_excel(self, data: dict, filename: str):
        return self.excel_handler.write_to_excel(data, filename)


class SYSHandlerService:
    def __init__(self, sys_handler: ISYSHandler):
        self.sys_handler = sys_handler

    async def start_monitoring(self,) -> bool:
        return await self.sys_handler.start_monitoring()
