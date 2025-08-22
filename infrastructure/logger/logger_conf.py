import logging
import asyncio
from core import IRedisClient
import colorlog
import inspect
from pathlib import Path
import time
import json
from core import IRobotLogger


class RobotLogger(IRobotLogger):
    SUCCESS_LEVEL = 25

    def __init__(self, log_path: Path, redis_client: IRedisClient = None, max_log_size: int = 1_000_000):
        self._logger = logging.getLogger("RobotLogger")
        self._logger.setLevel(logging.DEBUG)
        self.max_log_size = max_log_size
        self.log_path = log_path
        self.redis_client = redis_client

        logging.addLevelName(self.SUCCESS_LEVEL, "SUCCESS")
        self._logger.success = lambda message, *args, **kwargs: self._logger.log(self.SUCCESS_LEVEL, message, *args, **kwargs)

        self._add_file_handler()
        self._add_console_handler()

    def _add_file_handler(self):
        """Добавляем обработчик для записи в файл (все логи)."""
        file_handler = logging.FileHandler(self.log_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s - %(extra)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        self._logger.addHandler(file_handler)

    def _add_console_handler(self):
        """Добавляем обработчик для вывода в консоль с цветами."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(colorlog.ColoredFormatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s - %(extra)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'SUCCESS': 'bold_green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        ))
        self._logger.addHandler(console_handler)

    def _log_and_notify(self, level: str, message: str, extra: dict = None):
        """Записываем в лог и отправляем уведомление в Telegram, если уровень ошибки или критичный."""
        frame = inspect.stack()[2]
        caller_filename = Path(frame.filename).name
        caller_function = frame.function
        caller_line = frame.lineno

        extra_str = json.dumps(extra, ensure_ascii=False) if extra else ""
        detailed_message = f"{caller_filename}:{caller_line} - {caller_function} - {message} {extra_str}"

        getattr(self._logger, level)(detailed_message, extra={'extra': extra_str})

    def clear_log_file(self):
        """Очистка содержимого лог-файла."""
        with open(self.log_path, 'w', encoding='utf-8') as log_file:
            log_file.truncate(0)

    def _get_logs_from_file(self) -> str:
        """Получение всех логов из файла."""
        with open(self.log_path, 'r', encoding='utf-8') as log_file:
            return log_file.read()

    def _send_notification(self, type: str, log_file: bool = True, file_path: Path = None, excel_file: bool = True):
        """Отправляет уведомления в очередь."""
        message = {'type': type}
        if log_file:
            message['log_file_path'] = str(self.log_path)
        if file_path:
            message['file_name'] = file_path.name
            if excel_file:
                message['excel_file_path'] = file_path.name
        self.redis_client.push_to_queue("logs_queue", message)

    def verify_logs_and_alert(self, file_path: Path = None):
        """Обработка и отправка уведомлений."""
        logs = self._get_logs_from_file()
        notification_map = {
            "CRITICAL": {"type": 'CRITICAL', "log_file": True, "excel_file": False},
            "ERROR": {"type": 'ERROR', "log_file": True, "excel_file": True},
            "SUCCESS": {"type": "SUCCESS", "log_file": True, "excel_file": False}
        }
        for log_type, params in notification_map.items():
            if log_type in logs:
                self._send_notification(**params, file_path=file_path)
                break
        time.sleep(3)
        self.clear_log_file()

    def success(self, message: str, extra: dict = None):
        self._log_and_notify("success", message, extra)

    def debug(self, message: str, extra: dict = None) -> None:
        self._log_and_notify("debug", message, extra)

    def info(self, message: str, extra: dict = None) -> None:
        """Логирование уровня INFO."""
        self._log_and_notify("info", message, extra)

    def error(self, message: str, extra: dict = None) -> None:
        """Логирование уровня ERROR."""
        self._log_and_notify("error", message, extra)

    def critical(self, message: str, extra: dict = None) -> None:
        """Логирование уровня CRITICAL."""
        self._log_and_notify("critical", message, extra)
