from ebaysdk.finding import Connection as Finding
from ebaysdk.trading import Connection as Trading
from typing import Protocol, Optional
from core import IEbay
from settings.config import Ebay
from core import IRobotLogger


class IEliminationFilter(Protocol):
    @staticmethod
    def filter(key: str) -> str:
        """Filter key to ensure it's cleaned and normalized."""
        ...


class EbayCom(IEbay):
    """
    Класс для работы с eBay API, выполняет поиск и фильтрацию позиций на сайте.
    """

    BASE_PAYLOAD = {
        'paginationInput': {'entriesPerPage': 15},
        'itemFilter': [{'name': 'LocatedIn', 'value': 'WorldWide'}]
    }

    def __init__(self, settings_ebay: Ebay, robot_logger: IRobotLogger):
        self.api_key = settings_ebay.api_key
        self.cert_id = settings_ebay.cert_id
        self.dev_id = settings_ebay.dev_id
        self.token = settings_ebay.token
        self.robot_logger = robot_logger

    def _get_finding_api(self) -> Finding:
        """Создание подключения к Finding API."""
        try:
            return Finding(appid=self.api_key, config_file=None, siteid='EBAY-US')
        except Exception as e:
            self.robot_logger.critical(f"Ошибка создания подключения к Finding API: {e}")
            raise

    def _get_trading_api(self) -> Trading:
        """Создание подключения к Trading API."""
        try:
            return Trading(appid=self.api_key, config_file=None,
                           certid=self.cert_id, devid=self.dev_id, token=self.token)
        except Exception as e:
            self.robot_logger.critical(f"Ошибка создания подключения к Trading API: {e}")
            raise

    def _search_items(self, key: str, vendor: str) -> Optional[list]:
        """Ищет товары по ключевым словам и возвращает результаты поиска."""
        payload = self.BASE_PAYLOAD.copy()
        payload['keywords'] = f"{vendor} {key}"

        try:
            api = self._get_finding_api()
            response = api.execute('findItemsAdvanced', payload)
            search_count = response.reply.searchResult._count
            if search_count == 0:
                self.robot_logger.info(f"По запросу {payload['keywords']} ничего не найдено.")
                return None
            self.robot_logger.success(f"Найдено {search_count} позиций для {payload['keywords']}.")
            return response.reply.searchResult.item
        except Exception as e:
            self.robot_logger.error(f"Ошибка поиска товаров (ключ {key}, вендор {vendor}): {e}")
            return None

    def _check_item_specifics(self, item_id: str, key: str, ifilter: IEliminationFilter) -> bool:
        """Проверяет наличие ключа среди характеристик товара."""
        try:
            api = self._get_trading_api()
            response = api.execute('GetItem', {'ItemID': item_id, 'IncludeItemSpecifics': True})
            specifics = response.reply.Item.ItemSpecifics.NameValueList
            for specific in specifics:
                if specific.Name in ('Model', 'MPN'):
                    filtered_value = ifilter.filter(specific.Value)
                    if key in filtered_value or filtered_value in key:
                        self.robot_logger.success(f"Точное совпадение MPN, Model: {key} {filtered_value}")
                        return True
            self.robot_logger.info(f"Нет совпадений по характеристикам для {item_id}.")
            return False
        except Exception as e:
            self.robot_logger.error(f"Ошибка проверки характеристик товара {item_id}: {e}")
            return False

    def _initialize_context(self) -> dict:
        """Инициализирует и возвращает стандартный контекст для товара."""
        return {
            'URL': 'Нет результатов.',
            'СТОИМОСТЬ ТОВАРА/USD': 0
        }

    def _find_exact_match(self, items, filtered_key: str, ifilter: IEliminationFilter, context: dict, item_atr: dict) -> bool:
        """Ищет прямое совпадение с ключом в заголовках товаров."""
        self.robot_logger.debug(f"Поиск точного совпадения для ключа: {filtered_key}.")
        for item in items:
            item_words = [ifilter.filter(word) for word in item.title.split()]
            if filtered_key in item_words:
                url = item.viewItemURL
                self.robot_logger.info(f"Проверка товара: URL: {url} ItemID {item.itemId}")
                if self._check_item_specifics(item.itemId, filtered_key, ifilter):
                    price = item.sellingStatus.currentPrice.value
                    context['URL'] = url
                    context['СТОИМОСТЬ ТОВАРА/USD'] = round(float(price))
                    item_atr.update(context)
                    self.robot_logger.success(f'Нашли - URL: {url}, СТОИМОСТЬ ТОВАРА/USD: {price}')
                    return True
        return False

    def _find_best_match(self, items, filtered_key: str, ifilter: IEliminationFilter) -> Optional[dict]:
        """Ищет наиболее близкое по длине совпадение с ключом."""
        try:
            self.robot_logger.debug(f"Поиск лучшего совпадения для ключа: {filtered_key}.")
            best_match = None
            min_length_diff = float('inf')

            for item in items:
                item_words = [ifilter.filter(word) for word in item.title.split()]
                for filtered_word in item_words:
                    if filtered_key in filtered_word or filtered_word in filtered_key:
                        length_diff = abs(len(filtered_key) - len(filtered_word))
                        if length_diff < min_length_diff:
                            min_length_diff = length_diff
                            best_match = {
                                'URL': item.viewItemURL,
                                'СТОИМОСТЬ ТОВАРА/USD': round(float(item.sellingStatus.currentPrice.value))
                            }
                            self.robot_logger.info(f"Промежуточное совпадение: {filtered_key} -> {filtered_word}.")
            return best_match
        except Exception as e:
            self.robot_logger.error(f"Ошибка поиска ближайшего совпадения: {e}")
            return None

    def searchebay(self, item_atr: dict, key: str, vendor: str, ifilter: IEliminationFilter) -> None:
        """Выполняет поиск товара и обновляет его контекст."""
        try:
            self.robot_logger.debug("Инициализация контекста.")
            context = self._initialize_context()
            item_atr.update(context)

            filtered_key = ifilter.filter(key)

            self.robot_logger.debug("Начало поиска объявлений.")
            items = self._search_items(key, vendor)
            if not items:
                return

            self.robot_logger.debug("Поиск точного совпадения.")
            if self._find_exact_match(items, filtered_key, ifilter, context, item_atr):
                return

            self.robot_logger.debug("Поиск лучшего совпадения.")
            best_match = self._find_best_match(items, filtered_key, ifilter)
            if best_match:
                item_atr.update(best_match)
        except Exception as e:
            self.robot_logger.critical(f"Ошибка выполнения поиска ebay: {e}")
