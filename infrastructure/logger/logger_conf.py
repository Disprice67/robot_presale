import logging
import asyncio
from core import IRobotLogger
import colorlog
import inspect
from pathlib import Path


class RobotLogger(IRobotLogger):
    SUCCESS_LEVEL = 25

    def __init__(self, log_path: Path):
        self._logger = logging.getLogger("RobotLogger")
        self._logger.setLevel(logging.DEBUG)
        self.log_path = log_path

        logging.addLevelName(self.SUCCESS_LEVEL, "SUCCESS")
        self._logger.success = lambda message, *args, **kwargs: self._logger.log(self.SUCCESS_LEVEL, message, *args, **kwargs)

        self._add_file_handler()
        self._add_console_handler()

    def _add_file_handler(self):
        """Добавляем обработчик для записи в файл (все логи)."""
        file_handler = logging.FileHandler(self.log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s")
        )
        self._logger.addHandler(file_handler)

    def _add_console_handler(self):
        """Добавляем обработчик для вывода в консоль с цветами."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(colorlog.ColoredFormatter(
            "%(asctime)s - %(levelname)s - %(message)s",
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

    async def _send_to_telegram(self, message: str):
        """Асинхронная отправка сообщения в Telegram."""
        ...
        # try:
        #     await self.bot.send_message(self.chat_id, message, parse_mode=ParseMode.MARKDOWN)
        # except Exception as e:
        #     self._logger.error(f"Не удалось отправить лог в Telegram: {e}")

    def _log_and_notify(self, level: str, message: str):
        """Записываем в лог и отправляем уведомление в Telegram, если уровень ошибки или критичный."""
        frame = inspect.stack()[2]
        caller_filename = frame.filename
        caller_function = frame.function
        caller_line = frame.lineno

        detailed_message = f"{caller_filename}:{caller_line} - {caller_function} - {message}"

        getattr(self._logger, level)(detailed_message)

        # if level in ["error", "critical"]:
        #     asyncio.create_task(self._send_to_telegram(f"*{level.upper()}*: {message}"))

    def success(self, message: str):
        self._log_and_notify("success", message)

    def debug(self, message: str) -> None:
        self._log_and_notify("debug", message)

    def info(self, message: str) -> None:
        """Логирование уровня INFO."""
        self._log_and_notify("info", message)

    def error(self, message: str) -> None:
        """Логирование уровня ERROR."""
        self._log_and_notify("error", message)

    def critical(self, message: str) -> None:
        """Логирование уровня CRITICAL."""
        self._log_and_notify("critical", message)
