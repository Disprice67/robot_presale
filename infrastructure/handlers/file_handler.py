from ..database.db_repository import DatabaseRepository
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from core import IMonitorFiles, IRobotLogger
from pathlib import Path
import asyncio


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, database_repository: DatabaseRepository, robot_logger: IRobotLogger):
        self.database_repository = database_repository
        self.robot_logger = robot_logger

    def on_modified(self, event):
        path_name = Path(event.src_path)
        if not event.is_directory and path_name.name.endswith(('.xlsx',)) and '~$' not in path_name.name:
            asyncio.create_task(self.database_repository.update_table(event))
            self.robot_logger.info(f'Директория обновлена {event.src_path}')


class MonitorFiles(IMonitorFiles):
    def __init__(self, database_repository: DatabaseRepository, robot_logger: IRobotLogger, file_event_handler: FileEventHandler):
        self.database_repository = database_repository
        self.robot_logger = robot_logger
        self.file_event_handler = file_event_handler

    def start_monitoring(self, directory_paths: list[str]):
        try:
            observers = []
            for path in directory_paths:
                observer = PollingObserver()
                observer.schedule(self.file_event_handler, path=path, recursive=True)
                observer.start()
                observers.append(observer)
                self.robot_logger.info(f'Директория {path} мониторится.')
            self.robot_logger.success('Мониторинг сетевых папок запущен.')
            return observers
        except Exception as e:
            self.robot_logger.error(f'Ошибка при мониторинге сетевых папок {e}')