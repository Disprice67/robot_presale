from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from typing import Optional, Union, List
from core import IRobotLogger, IPartNumberFilter
import re
import asyncio
import json
import os
from datetime import datetime
import random


class YandexMarketParser:
    def __init__(self, robot_logger: IRobotLogger, usd_rate: int = 100):
        self.robot_logger = robot_logger
        self.base_url = "https://market.yandex.ru"
        self.usd_rate = usd_rate
        self.playwright = None
        self.browser = None

        self.raw_urls_file = "yandex_market_raw_urls.json"

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
            self.robot_logger.error(f"Yandex Market: ошибка при сохранении сырых URL: {e}")

    async def _initialize_browser(self):
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox"
                ]
            )

    async def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        if not self.browser:
            await self._initialize_browser()
        page = await self.browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://market.yandex.ru/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive"
            }
        )
        try:
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            await page.goto(url, wait_until="domcontentloaded", timeout=5000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_selector("div[data-apiary-widget-name='@marketfront/SerpEntity']", timeout=5000)
            html = await page.content()
            self.robot_logger.info(f"Yandex Market: успешно загружена страница {url}")
            return BeautifulSoup(html, "html.parser")
        except PlaywrightTimeoutError as e:
            self.robot_logger.error(f"Yandex Market: таймаут ожидания загрузки или элемента на {url} -> {e}")
            return None
        except Exception as e:
            self.robot_logger.error(f"Yandex Market: ошибка при загрузке {url} -> {e}")
            return None
        finally:
            await page.close()

    def _extract_price_rub(self, block: BeautifulSoup) -> Optional[float]:
        price_tag = block.find("span", attrs={"data-auto": "snippet-price-current"})
        if not price_tag:
            return None
        try:
            first_span = price_tag.find("span")
            price_text = first_span.get_text(strip=True)
            cleaned_price = re.sub(r'[^\d]', '', price_text)
            return float(cleaned_price)
        except (ValueError, AttributeError):
            return None

    def _parse_item_block(self, block: BeautifulSoup, normalized_part_number: str, ifilter: IPartNumberFilter) -> Optional[dict]:
        if not block.get("data-apiary-widget-name") == "@marketfront/SerpEntity":
            return None

        link_tag = block.find("a", attrs={"data-auto": "snippet-link"})
        if not link_tag or not link_tag.get("href"):
            return None

        title_tag = block.find("span", attrs={"data-auto": "snippet-title"})
        title = title_tag.get_text(strip=True) if title_tag else ""
        title_words = [ifilter.normalize_part_number(word) for word in title.split()]
        if normalized_part_number not in title_words:
            return None

        url = f"{self.base_url}{link_tag['href']}" if not link_tag['href'].startswith("http") else link_tag['href']
        price_rub = self._extract_price_rub(block)
        price_usd = round(price_rub / self.usd_rate, 2) if price_rub else None

        if not price_rub:
            return None

        return {
            "url": url,
            "price_usd": price_usd,
            "title": title
        }

    def _select_best_item(self, results: List[dict]) -> dict:
        best_item = min(results, key=lambda x: x["price_usd"])
        self.robot_logger.info(
            f"Yandex Market: выбран товар {best_item['url']} с ценой ({best_item['price_usd']} USD)"
        )
        return {
            "URL": best_item["url"],
            "СТОИМОСТЬ ТОВАРА/USD": best_item["price_usd"],
            "СТОИМОСТЬ ДОСТАВКИ/USD": 0
        }

    async def search_by_part_number(self, item: dict, part_number: str, vendor: str, ifilter: IPartNumberFilter) -> Union[dict, None]:
        normalized_part_number = ifilter.normalize_part_number(part_number)
        search_url = f"{self.base_url}/search?text={part_number}"

        soup = await self._fetch_page(search_url)
        if not soup:
            self.robot_logger.info(f"Yandex Market: информации по парт-номеру {part_number} нет.")
            return None

        items = soup.find_all("div", attrs={"data-apiary-widget-name": "@marketfront/SerpEntity"})
        self.robot_logger.info(f"Yandex Market: найдено {len(items)} товаров для {part_number}")

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

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
