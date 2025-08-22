from typing import Protocol
from pathlib import Path


class IRedisClient(Protocol):
    def push_to_queue(self, queue_name: str, message: dict):
        """Добавить сообщение в очередь."""
        ...

    def get_from_queue(self, queue_name: str):
        """Извлечь сообщение из очереди."""
        ...


class IRobotLogger(Protocol):

    def verify_logs_and_alert(self, file_path: Path = None):
        """Обработка и отправка уведомлений."""
        ...

    def success(self, message: str, extra: dict = None):
        """Логирование уровня SUCCESS."""
        ...

    def debug(self, message: str, extra: dict = None) -> None:
        """Логирование уровня DEBUG."""
        ...

    def info(self, message: str, extra: dict = None) -> None:
        """Логирование уровня INFO."""
        ...

    def error(self, message: str, extra: dict = None) -> None:
        """Логирование уровня ERROR."""
        ...

    def critical(self, message: str, extra: dict = None) -> None:
        """Логирование уровня CRITICAL."""
        ...
