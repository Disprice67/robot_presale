import aiohttp
from typing import Optional
from core import IEbay
from settings.config import Ebay
from core import IRobotLogger, IPartNumberFilter
import base64
import asyncio
import json
from datetime import datetime
import os


class EbayCom(IEbay):
    BASE_URL = "https://api.ebay.com"
    BROWSE_API = f"{BASE_URL}/buy/browse/v1/item_summary/search"
    ITEM_API = f"{BASE_URL}/buy/browse/v1/item/"
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    METADATA_API = f"{BASE_URL}/commerce/taxonomy/v1/get_default_category_tree_id"

    BASE_PAYLOAD = {
        "limit": 15,
        "filter": "deliveryCountry:WorldWide"
    }

    def __init__(self, settings_ebay: Ebay, robot_logger: IRobotLogger):
        self.app_id = settings_ebay.app_id
        self.client_secret = settings_ebay.client_secret
        self.robot_logger = robot_logger
        self.access_token = None

        self.raw_urls_file = "ebay_raw_urls.json"

    async def _save_raw_urls(self, part_number: str, urls: list[str]):
        """Сохраняет все найденные URL в файл перед фильтрацией."""
        try:
            data = {}
            if os.path.exists(self.raw_urls_file):
                with open(self.raw_urls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            timestamp = datetime.now().isoformat()
            data[timestamp] = {
                'part_number': part_number,
                'urls': urls
            }

            with open(self.raw_urls_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.robot_logger.error(f"Ebay: ошибка при сохранении сырых URL: {e}")

    async def _refresh_token(self):
        """Запрашиваем новый Application Token асинхронно."""
        try:
            auth = base64.b64encode(f"{self.app_id}:{self.client_secret}".encode()).decode()
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth}"
            }
            data = {
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.TOKEN_URL, headers=headers, data=data) as response:
                    response.raise_for_status()
                    token_data = await response.json()
                    self.access_token = token_data["access_token"]
                    self.robot_logger.success("Новый токен получен.")
        except aiohttp.ClientError as e:
            self.robot_logger.critical(f"Ошибка получения токена: {e}")
            raise

    async def _check_token_status(self) -> bool:
        """Проверяет статус токена через тестовый запрос."""
        if not self.access_token:
            self.robot_logger.debug("Токен истек или отсутствует, обновляем.")
            await self._refresh_token()
            return True

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                "Accept": "application/json"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.METADATA_API}?marketplace_id=EBAY_US", headers=headers) as response:
                    if response.status == 401:
                        self.robot_logger.debug("Токен недействителен, обновляем")
                        await self._refresh_token()
                    return True
        except aiohttp.ClientError as e:
            self.robot_logger.error(f"Неожиданная ошибка проверки токена: {e}")
            return False

    async def _get_headers(self) -> dict:
        """Формирование заголовков для запросов с проверкой токена."""
        if not await self._check_token_status():
            self.robot_logger.critical("Не удалось получить валидный токен.")
            raise ValueError("Токен недоступен")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }

    async def _search_items(self, key: str, vendor: str) -> Optional[list]:
        """Ищет товары по ключевым словам и возвращает результаты поиска."""
        params = self.BASE_PAYLOAD.copy()
        params["q"] = f"{vendor} {key}"

        try:
            headers = await self._get_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BROWSE_API, headers=headers, params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    items = data.get("itemSummaries", [])
                    search_count = len(items)
                    if search_count == 0:
                        self.robot_logger.info(f"По запросу {params['q']} ничего не найдено.")
                        return None

                    # all_urls = [item.get("itemWebUrl", "") for item in items if item.get("itemWebUrl")]
                    # await self._save_raw_urls(key, all_urls)

                    self.robot_logger.success(f"Найдено {search_count} позиций для {params['q']}.")
                    return items
        except aiohttp.ClientError as e:
            self.robot_logger.error(f"Ошибка поиска товаров (ключ {key}, вендор {vendor}): {e}")
            return None

    async def _check_item_specifics(self, item_id: str, key: str, ifilter: IPartNumberFilter) -> bool:
        """Проверяет наличие ключа среди характеристик товара."""
        try:
            headers = await self._get_headers()
            url = f"{self.ITEM_API}{item_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    item = await response.json()
                    specifics = item.get("additionalProductInformation", {}).get("attributes", [])
                    if not specifics:
                        self.robot_logger.info(f"Для {item_id} нет расширенных параметров.")
                        return False
                    for specific in specifics:
                        if specific.get("name") in ("Model", "MPN"):
                            filtered_value = ifilter.normalize_part_number(specific.get("value", ""))
                            if key in filtered_value or filtered_value in key:
                                self.robot_logger.success(f"Точное совпадение MPN, Model: {key} {filtered_value}")
                                return True
                    self.robot_logger.info(f"Нет совпадений по характеристикам для {item_id}.")
                    return False
        except aiohttp.ClientError as e:
            self.robot_logger.error(f"Ошибка проверки характеристик товара {item_id}: {e}")
            return False

    def _initialize_context(self) -> dict:
        """Инициализирует и возвращает стандартный контекст для товара."""
        return {
            'URL': 'Нет результатов.',
            'СТОИМОСТЬ ТОВАРА/USD': 0
        }

    async def _find_exact_match(self, items, key: str, ifilter: IPartNumberFilter, context: dict, ) -> bool:
        """Ищет прямое совпадение с ключом в заголовках товаров."""
        self.robot_logger.debug(f"Поиск точного совпадения для ключа: {key}.")
        for item in items:
            item_words = [ifilter.normalize_part_number(word) for word in item.get("title", "").split()]
            filtered_key = ifilter.normalize_part_number(key)
            if filtered_key in item_words:
                url = item.get("itemWebUrl")
                item_id = item.get("itemId")
                self.robot_logger.info(f"Проверка товара: URL: {url} ItemID {item_id}")
                if await self._check_item_specifics(item_id, key, ifilter):
                    price = item.get("price", {}).get("value", 0)
                    context['URL'] = url
                    context['СТОИМОСТЬ ТОВАРА/USD'] = round(float(price))
                    self.robot_logger.success(f'Нашли - URL: {url}, СТОИМОСТЬ ТОВАРА/USD: {price}')
                    return context
        return False

    async def _find_best_match(self, items, key: str, ifilter: IPartNumberFilter) -> Optional[dict]:
        """Ищет наиболее близкое по длине совпадение с ключом."""
        try:
            self.robot_logger.debug(f"Поиск лучшего совпадения для ключа: {key}.")
            best_match = None
            min_length_diff = float('inf')
            filtered_key = ifilter.normalize_part_number(key)
            for item in items:
                item_words = [ifilter.normalize_part_number(word) for word in item.get("title", "").split()]
                for filtered_word in item_words:
                    if filtered_key in filtered_word or filtered_word in filtered_key:
                        length_diff = abs(len(filtered_key) - len(filtered_word))
                        if length_diff < min_length_diff:
                            min_length_diff = length_diff
                            best_match = {
                                'URL': item.get("itemWebUrl"),
                                'СТОИМОСТЬ ТОВАРА/USD': round(float(item.get("price", {}).get("value", 0)))
                            }
                            self.robot_logger.info(f"Промежуточное совпадение: {filtered_key} -> {filtered_word}.")
            return best_match
        except Exception as e:
            self.robot_logger.error(f"Ошибка поиска ближайшего совпадения: {e}")
            return None

    async def searchebay(self, item_atr: dict, key: str, vendor: str, ifilter: IPartNumberFilter):
        """Выполняет поиск товара и обновляет его контекст."""
        try:
            self.robot_logger.debug("Инициализация контекста.")
            context = self._initialize_context()
            item_atr.update(context)

            self.robot_logger.debug("Начало поиска объявлений.")
            items = await self._search_items(key, vendor)
            if not items:
                return

            self.robot_logger.debug("Поиск точного совпадения.")
            if await self._find_exact_match(items, key, ifilter, context):
                return

            self.robot_logger.debug("Поиск лучшего совпадения.")
            best_match = await self._find_best_match(items, key, ifilter)
            if best_match:
                return best_match
        except Exception as e:
            self.robot_logger.critical(f"Ошибка выполнения поиска ebay: {e}")
