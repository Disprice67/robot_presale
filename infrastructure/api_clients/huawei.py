import aiohttp
from typing import Optional
from core import IParsingHuawei, IRobotLogger
from settings.config import HuaweiData, HuaweiHeader


class ParsingHuawei(IParsingHuawei):
    def __init__(self, huawei_data: HuaweiData, header: HuaweiHeader, robot_logger: IRobotLogger):
        self.url = str(huawei_data.url_huawei)
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

    async def _post_request(self, key: str) -> Optional[dict]:
        """Отправляет асинхронный POST-запрос и возвращает данные в формате JSON, если запрос успешен."""
        try:
            async with aiohttp.ClientSession() as session:
                self.payload['query'] = key
                async with session.post(self.url, headers=self.headers, json=self.payload, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('data', [])
        except aiohttp.ClientError as e:
            self.robot_logger.error(f"Ошибка при выполнении запроса: {e}")
            return None

    async def get_part_and_model(self, key: str) -> Optional[list[str]]:
        """Извлекает Part Number и Model из данных ответа."""
        self.robot_logger.debug(f'Начинаем парсинг HUAWEI для {key}')
        data = await self._post_request(key)
        if not data:
            self.robot_logger.info(f"Не получены данные для ключа: {key}")
            return None

        cardlist = data[0].get('entityCardList', [])
        if not isinstance(cardlist, list):
            self.robot_logger.error(f"Неверная структура данных для ключа: {key}. Ожидался список 'entityCardList'.")
            return None

        for element in cardlist:
            property_key = element.get('propertyKey')
            if property_key in self.information:
                self.information[property_key] = element.get('propertyValue', '')

        part_number = self.information['Part Number']
        model = self.information['Model']
        if part_number and model:
            self.robot_logger.success(f'Найден {part_number} и {model}')
            return [part_number, model]
        self.robot_logger.info(f"Не удалось найти 'Part Number' или 'Model' для ключа: {key}")
        return None
