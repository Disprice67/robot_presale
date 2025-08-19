from bs4 import BeautifulSoup
import aiohttp
from typing import List, Dict, Optional, Union
from core import IRobotLogger, IPartNumberFilter, IBouz
import os
from datetime import datetime
import json


class BouzParser(IBouz):
    def __init__(self, robot_logger: IRobotLogger, usd_rate: int = 100):
        self.robot_logger = robot_logger
        self.base_url = "https://bouz.ru"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        self.usd_rate = usd_rate

        self.raw_urls_file = "bouz_raw_urls.json"

    async def _save_raw_urls(self, part_number: str, urls: List[str]):
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
            self.robot_logger.error(f"Bouz: ошибка при сохранении сырых URL: {e}")

    async def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Загружает страницу и возвращает объект BeautifulSoup."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    response.raise_for_status()
                    text = await response.text()
                    return BeautifulSoup(text, "html.parser")
        except aiohttp.ClientError as e:
            self.robot_logger.error(f"Bouz: ошибка при загрузке {url} -> {e}")
            return None

    def _extract_price_rub(self, block: BeautifulSoup) -> Optional[int]:
        """Извлекает цену в рублях."""
        tag = block.find("span", class_="price_value")
        if not tag:
            return None
        try:
            return int(tag.get_text(strip=True).replace(" ", ""))
        except ValueError:
            return None

    def _extract_price_usd(self, block: BeautifulSoup) -> Optional[float]:
        """Извлекает цену в долларах."""
        tag = block.find("div", class_="price_dol_originls")
        if not tag:
            return None
        try:
            return float(tag.get_text(strip=True).replace("$", "").replace(" ", ""))
        except ValueError:
            return None

    def _parse_item_block(
        self, block: BeautifulSoup, normalized_part_number: str, ifilter: IPartNumberFilter
    ) -> Optional[Dict]:
        """Парсит один блок товара и возвращает словарь с url и ценой."""
        title_tag = block.find("div", class_="item-title")
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)
        normalized_title = ifilter.normalize_part_number(title).replace(" ", "")

        if normalized_part_number not in normalized_title:
            return None

        link_tag = title_tag.find("a")
        url = f"{self.base_url}{link_tag['href']}" if link_tag and link_tag.has_attr("href") else None

        rub_price = self._extract_price_rub(block)
        usd_price = self._extract_price_usd(block)

        if not rub_price and not usd_price:
            return None

        if rub_price and not usd_price:
            usd_price = rub_price / self.usd_rate

        return {
            "url": url,
            "price_usd": usd_price
        }

    def _select_best_item(self, results: List[Dict]) -> Dict:
        """Выбирает товар с минимальной ценой."""
        best_item = min(results, key=lambda x: x["price_usd"])
        self.robot_logger.info(
            f"Bouz: выбран товар {best_item['url']} с ценой {best_item['price_usd']} USD"
        )
        return {
            "URL": best_item["url"],
            "СТОИМОСТЬ ТОВАРА/USD": best_item["price_usd"],
            "СТОИМОСТЬ ДОСТАВКИ/USD": 0
        }

    async def search_by_part_number(
        self,
        item: dict,
        part_number: str,
        vendor: str,
        ifilter: IPartNumberFilter
    ) -> Union[Dict, None]:
        """Ищет товары по парт-номеру на bouz.ru и возвращает JSON-совместимый словарь."""
        normalized_part_number = ifilter.normalize_part_number(part_number)
        catalog_url = f"{self.base_url}/catalog/?q={vendor}+{part_number}"

        soup = await self._fetch_page(catalog_url)
        if not soup:
            self.robot_logger.info(f"Bouz: информации по парт-номеру {part_number} нет.")
            return None

        items = soup.find_all("div", class_="catalog-block-view__item")
        self.robot_logger.info(f"Bouz: найдено {len(items)} товаров для {part_number}")

        results = []
        # all_urls = []
        for block in items:
            parsed = self._parse_item_block(block, normalized_part_number, ifilter)
            if parsed:
                results.append(parsed)
        #         all_urls.append(parsed["url"])

        # await self._save_raw_urls(part_number, all_urls)

        if not results:
            return None

        return self._select_best_item(results)
