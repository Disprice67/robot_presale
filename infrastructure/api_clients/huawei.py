import requests
from typing import Optional
from core import IParsingHuawei, IRobotLogger
from settings.config import HuaweiData, HuaweiHeader


class ParsingHuawei(IParsingHuawei):
    def __init__(self, huawei_data: HuaweiData, header: HuaweiHeader, robot_logger: IRobotLogger):
        self.url = huawei_data.url_huawei
        self.information = {
            'Part Number': '',
            'Model': ''
        }
        self.headers = {'User-Agent': header.user_agent}
        self.payload = {
            "query": '',
            "lang": "en",
            "domain": "0",
        }
        self.robot_logger = robot_logger

    def _post_request(self, key: str) -> Optional[dict]:
        """Отправляет POST-запрос и возвращает данные в формате JSON, если запрос успешен."""
        try:
            self.payload['quary'] = key
            response = requests.post(self.url, headers=self.headers, json=self.payload, verify=False)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except requests.RequestException as e:
            self.robot_logger.error(f"Ошибка при выполнении запроса: {e}")
            return None

    def get_part_and_model(self, key: str) -> Optional[list[str]]:
        """Извлекает Part Number и Model из данных ответа."""
        self.robot_logger.debug('Начинаем парсинг HUAWEI')
        data = self._post_request(key)
        if not data:
            self.robot_logger.info(f"Не получены данные для ключа: {key}")
            return None

        cardlist = data.get('entityCardList', [])
        if not isinstance(cardlist, list):
            self.robot_logger.error(f"Неверная структура данных для ключа: {key}. Ожидался список 'entityCardList'.")
            return None

        for element in cardlist:
            key = element.get('propertyKey')
            if key in self.information:
                self.information[key] = element.get('propertyValue', '')

        part_number = self.information['Part Number']
        model = self.information['Model']
        if part_number and model:
            self.robot_logger.success(f'Найден {part_number} и {model}')
            return [part_number, model]
        self.robot_logger.info(f"Не удалось найти 'Part Number' или 'Model' для ключа: {key}")
        return None
