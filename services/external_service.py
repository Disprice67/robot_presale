from core.interfaces.i_external import IEbay, IEmail, IParsingHuawei, IBouz, INag, IYandexMarket
from core import IPartNumberFilter, IRobotLogger
from typing import Optional
from pathlib import Path
import asyncio
import random


class ExternalSearchService:
    def __init__(self, bouz: IBouz, nag: INag, ebay: IEbay, yandex_market: IYandexMarket, robot_logger: IRobotLogger, usd_rate: int = 100):
        self.bouz = bouz
        self.nag = nag
        self.ebay = ebay
        self.yandex_market = yandex_market
        self.robot_logger = robot_logger
        self.usd_rate = usd_rate

        self.semaphore_parsers = asyncio.Semaphore(5)

    async def _search_on_source(self, source_name: str, search_func, item: dict, part_number: str, vendor: str, ifilter: IPartNumberFilter) -> Optional[dict]:
        """Выполняет поиск на указанном источнике и логирует результат."""
        try:
            if source_name in ["Bouz", "YandexMarket"]:
                async with self.semaphore_parsers:
                    delay = random.uniform(0.3, 1.5)
                    self.robot_logger.info(f"{source_name}: случайная задержка {delay:.2f} сек перед поиском {part_number}")
                    await asyncio.sleep(delay)
                    result = await search_func(item, part_number, vendor, ifilter)
            else:
                result = await search_func(item, part_number, vendor, ifilter)

            if result:
                self.robot_logger.info(f"{source_name}: найден результат - URL: {result.get('URL')}, Стоимость: {result.get('СТОИМОСТЬ ТОВАРА USD')} USD")
                return result
            self.robot_logger.info(f"{source_name}: ничего не найдено для {part_number}")
            return None
        except Exception as e:
            self.robot_logger.error(f"{source_name}: ошибка при поиске {part_number} -> {e}")
            return None

    async def search(self, item: dict, part_number: str, vendor: str, ifilter: IPartNumberFilter) -> Optional[dict]:
        """Выполняет последовательный поиск на Bouz, YandexMarket, eBay и возвращает первый найденный результат."""
        result = await self._search_on_source("Bouz", self.bouz.search_by_part_number, item, part_number, vendor, ifilter)
        if result:
            item.update(result)
            return None

        result = await self._search_on_source("YandexMarket", self.yandex_market.search_by_part_number, item, part_number, vendor, ifilter)
        if result:
            item.update(result)
            return None

        result = await self._search_on_source("eBay", self.ebay.searchebay, item, part_number, vendor, ifilter)
        if result:
            item.update(result)
            return None

        self.robot_logger.info(f"Ни один источник не нашел {part_number}")
        return None


class EmailService:
    def __init__(self, email: IEmail,):
        self.email = email

    def get_file_list(self) -> list[Path]:
        return self.email.get_file_list()

    def clear_file_list(self) -> None:
        self.email.clear_file_list()

    def download_attachments(self,) -> bool:
        return self.email.download_attachments()

    def send_email(self, attachments: Path, sheet_name: str):
        return self.email.send_email(attachments, sheet_name)


class HuaweiService:
    def __init__(self, huawei: IParsingHuawei):
        self.huawei = huawei

    async def get_part_and_model(self, key: str) -> Optional[list[str]]:
        return await self.huawei.get_part_and_model(key)
