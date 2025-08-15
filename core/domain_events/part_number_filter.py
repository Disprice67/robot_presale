from core.interfaces.i_logger import IRobotLogger
import re
from fuzzywuzzy import fuzz


class PartNumberFilter:
    def __init__(self, robot_logger: IRobotLogger):
        self._robot_logger = robot_logger

    @staticmethod
    def normalize_part_number(part_number: str) -> str:
        """
        Нормализует парт-номер, оставляя только английские буквы, цифры и дефис.
        """
        normalized = re.sub(r'[^A-Za-zА-Яа-я0-9]', '', part_number)
        return normalized.upper()

    @staticmethod
    def calculate_similarity_score(query: str, db_value: str) -> float:
        """
        Вычисляет схожесть между запросом и значением из БД с учетом длины, структуры и суффиксов.
        """
        query = PartNumberFilter.normalize_part_number(query)
        db_value = PartNumberFilter.normalize_part_number(db_value)

        similarity = fuzz.token_sort_ratio(query, db_value)

        length_diff = abs(len(query) - len(db_value))
        max_len = max(len(query), len(db_value))
        length_penalty = max(0, 1 - (length_diff / max_len) ** 2)

        query_separators = query.count('-')
        db_separators = db_value.count('-')
        structure_bonus = 1.0 if query_separators == db_separators else 0.9

        suffix_length = 3
        query_suffix = query[-suffix_length:] if len(query) >= suffix_length else query
        db_suffix = db_value[-suffix_length:] if len(db_value) >= suffix_length else db_value
        suffix_bonus = 1.0 if query_suffix == db_suffix else 0.95

        return similarity * length_penalty * structure_bonus * suffix_bonus
