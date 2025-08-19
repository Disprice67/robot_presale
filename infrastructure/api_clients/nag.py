from bs4 import BeautifulSoup
import requests
from typing import Optional, Union
from core import IRobotLogger, IPartNumberFilter, IBouz


class NagParser(IBouz):
    """
    Парсер товаров с сайта shop.nag.ru.
    """

    def __init__(self, robot_logger: IRobotLogger, usd_rate: int = 100):
        self.robot_logger = robot_logger
        self.base_url = "https://shop.nag.ru"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        self.usd_rate = usd_rate

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Загружает страницу и возвращает объект BeautifulSoup, сохраняя HTML."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            self.robot_logger.info(f"Nag: успешно загружена страница {url}, статус: {response.status_code}")

            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            self.robot_logger.error(f"Nag: ошибка при загрузке {url} -> {e}")
            return None

    def _extract_price_usd(self, block: BeautifulSoup) -> Optional[float]:
        """Извлекает цену из тега our-price и конвертирует в USD."""
        price_tag = block.find("span", class_=["our-price", "body-xl"])
        if not price_tag:
            return None
        amount_tag = price_tag.find("span", class_="amount")
        if not amount_tag:
            return None
        try:
            price_text = amount_tag.get_text(strip=True).replace(" ", "").replace("₽", "").replace(",", ".")
            price_rub = float(price_text)
            return round(price_rub / self.usd_rate, 2)
        except ValueError:
            return None

    def _parse_item_block(
        self, block: BeautifulSoup, normalized_part_number: str, ifilter: IPartNumberFilter
    ) -> Optional[dict]:
        """
        Парсит один блок товара и возвращает словарь с url и ценой.
        Если данные некорректные или партномер не совпадает — возвращает None.
        """
        name_div = block.find("div", class_="setout__name")
        if not name_div:
            return None

        link_tag = name_div.find("a")
        if not link_tag or not link_tag.has_attr("href"):
            return None

        title = link_tag.get_text(strip=True)
        title_words = [ifilter.normalize_part_number(word) for word in title.split()]
        if normalized_part_number not in title_words:
            return None

        url = f"{self.base_url}{link_tag['href']}" if not link_tag['href'].startswith("http") else link_tag['href']
        price_usd = self._extract_price_usd(block)

        if not price_usd:
            return None

        return {
            "url": url,
            "price_usd": price_usd
        }

    def _select_best_item(self, results: list[dict]) -> dict:
        """
        Выбирает товар с минимальной ценой.
        """
        best_item = min(results, key=lambda x: x["price_usd"])
        self.robot_logger.info(
            f"Nag: выбран товар {best_item['url']} с ценой {best_item['price_usd']} USD"
        )
        return {
            "URL": best_item["url"],
            "СТОИМОСТЬ ТОВАРА/USD": best_item["price_usd"]
        }

    def search_by_part_number(
        self,
        item: dict,
        part_number: str,
        vendor: str,
        ifilter: IPartNumberFilter
    ) -> Union[dict, None]:
        """
        Ищет товары по парт-номеру на shop.nag.ru и возвращает JSON-совместимый словарь.
        """
        normalized_part_number = ifilter.normalize_part_number(part_number)
        search_url = f"{self.base_url}/search?search={part_number}"

        soup = self._fetch_page(search_url)
        if not soup:
            self.robot_logger.info(f"Nag: информации по парт-номеру {part_number} нет.")
            return None

        items = soup.find_all("div", class_="setout__item")
        self.robot_logger.info(f"Nag: найдено {len(items)} товаров для {part_number}")

        results = []
        for block in items:
            parsed = self._parse_item_block(block, normalized_part_number, ifilter)
            if parsed:
                results.append(parsed)

        if not results:
            return None

        return self._select_best_item(results)
