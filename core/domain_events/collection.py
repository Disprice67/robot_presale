from math import ceil
from core.interfaces.i_logger import IRobotLogger


class Economics:
    def __init__(self, robot_logger: IRobotLogger):
        self._robot_logger = robot_logger

    @staticmethod
    def costs_by_category(item: dict):
        """Calculation of repair and labor costs."""
        repair_one = item.get('РЕМОНТ')
        work_time_one = item.get('ТРУДОЗАТРАТЫ')
        amount = item.get('КОЛИЧЕСТВО')
        qty = item.get('QTY ИЗ АРХИВОВ')

        low_factor_archive = 0.75 if qty and qty > 100 else 1
        low_factor_amount = 0.5 if amount > 20 else 0.2 if amount > 10 else 1
        low_factor = low_factor_archive * low_factor_amount

        repair = (min(amount, 10) if amount <= 20 else amount) * repair_one * (low_factor if amount > 20 else 1)

        work = amount * work_time_one * (low_factor if amount > 10 else 1)

        one_unit_repair = ceil(repair / amount) if amount else 0
        one_unit_work = ceil(work / amount) if amount else 0

        costs = {
            'РЕМОНТЫ ЗА 1ЕД/РУБ': one_unit_repair,
            'ТРУДОЗАТРАТЫ ЗА 1ЕД/HOURS': one_unit_work
        }
        item.update(costs)
