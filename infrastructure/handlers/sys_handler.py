from ..api_clients.sys import ParsingSYS
from ..database.orm.models import Agreements
from pathlib import Path
from core import ISYSHandler, IRobotLogger
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SYSHandler(ISYSHandler):
    _agreement_dir = Agreements.__tablename__

    def __init__(self, parsing_sys: ParsingSYS, base_dir: Path, robot_logger: IRobotLogger):
        self.parsing_sys = parsing_sys
        self._base_dir = base_dir
        self.robot_logger = robot_logger

    async def _scheduler_update_sys(self, sys_dir: Path) -> None:
        """Асинхронное обновление SUS."""
        self.robot_logger.debug("Начало обновления SUS")
        await self.parsing_sys.parsing_active(sys_dir)
        self.robot_logger.debug("Обновление SUS завершено")

    async def start_monitoring(self) -> bool:
        """Запуск асинхронного мониторинга SUS с интервалом 3 дня."""
        try:
            fulldir = self._base_dir / self._agreement_dir
            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                self._scheduler_update_sys,
                'interval',
                minutes=1,  # Обновление каждые 3 дня
                args=[fulldir]
            )
            scheduler.start()
            self.robot_logger.success("Мониторинг SUS запущен")
            return True
        except Exception as e:
            self.robot_logger.error(f"Ошибка при запуске мониторинга СУС: {e}")
            return False
