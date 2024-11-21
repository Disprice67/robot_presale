from apscheduler.schedulers.background import BackgroundScheduler
from ..api_clients.sys import ParsingSYS
from ..database.orm.models import Agreements
from pathlib import Path
from core import ISYSHandler, IRobotLogger


class SYSHandler(ISYSHandler):
    _agreement_dir = Agreements.__tablename__

    def __init__(self, parsing_sys: ParsingSYS, base_dir: Path, robot_logger: IRobotLogger):
        self.parsing_sys = parsing_sys
        self._base_dir = base_dir
        self.robot_logger = robot_logger

    def _sheduler_update_sys(self, sys_dir: Path) -> None:
        self.parsing_sys.parsing_active(sys_dir)
        self.robot_logger.success('Договора из суса обновлены.')

    def start_monitoring(self) -> bool:
        try:
            fulldir = self._base_dir / self._agreement_dir
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                lambda: self._sheduler_update_sys(fulldir),
                'interval',
                days=1
            )
            scheduler.start()
            return True
        except Exception as e:
            self.robot_logger.error(f"Ошибка при запуске мониторинга СУСА: {e}")
            return False
