import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from openpyxl import Workbook
import pandas as pd
from settings.config import SysData, HuaweiHeader
from core import IRobotLogger
from io import BytesIO
import base64


class ParsingSYS:
    TAKE = 80
    TOKEN_URL = "https://fs.croc.ru/adfs/oauth2/token"

    def __init__(self, settings_sys: SysData, header: HuaweiHeader, robot_logger: IRobotLogger):
        self.url = settings_sys.url_sys_agreements
        self.client_id = settings_sys.client_id
        self.client_secret = settings_sys.client_secret
        self.robot_logger = robot_logger
        self.headers = {'User-Agent': header.user_agent}
        self.access_token = None
        self.token_expires_at = None
        self.params = {
            "columns": [
                {
                    "field": "redirectCol",
                    "title": "",
                    "width": 40,
                    "sortable": False,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": None,
                    "isIconColumn": True
                },
                {
                    "field": "crocCode",
                    "title": "КрокКод СДО",
                    "width": 150,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": "CrocCode",
                    "isIconColumn": False
                },
                {
                    "field": "hierarchicalNumber",
                    "title": "Иерархический номер",
                    "width": 200,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": "HierarchicalNumber",
                    "isIconColumn": False
                },
                {
                    "field": "organization.shortName",
                    "title": "Клиент",
                    "width": 300,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": "organization.displayName",
                    "excelExportName": "OrganizationName",
                    "isIconColumn": False
                },
                {
                    "field": "startDate",
                    "title": "Дата начала",
                    "width": 100,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": "StartDate",
                    "isIconColumn": False
                },
                {
                    "field": "endDate",
                    "title": "Дата окончания",
                    "width": 125,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": "EndDate",
                    "isIconColumn": False
                },
                {
                    "field": "activity.name",
                    "title": "Активность",
                    "width": 300,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": "activity.displayName",
                    "excelExportName": "ActivityName",
                    "isIconColumn": False
                },
                {
                    "field": "status",
                    "title": "Статус",
                    "width": 100,
                    "sortable": True,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": "Status",
                    "isIconColumn": False
                },
                {
                    "field": "executor.LastName",
                    "title": "Администратор",
                    "width": 200,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": "administrator",
                    "excelExportName": "AdministratorName",
                    "isIconColumn": False
                },
                {
                    "field": "currencyCode",
                    "title": "Валюта документа",
                    "width": 160,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "CurrencyCode",
                    "isIconColumn": False
                },
                {
                    "field": "prolongationAgreement",
                    "title": "Договор пролонгации",
                    "width": 180,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "ProlongationAgreement",
                    "isIconColumn": False
                },
                {
                    "field": "comment",
                    "title": "Комментарий",
                    "width": 260,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "Comment",
                    "isIconColumn": False
                },
                {
                    "field": "isRequiredNotifications",
                    "title": "Нотификация по заявкам",
                    "width": 200,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "IsRequiredNotifications",
                    "isIconColumn": False
                },
                {
                    "field": "refusalCause",
                    "title": "Причина отказа от пролонгации",
                    "width": 240,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": "refusalCause.displayName",
                    "excelExportName": "RefusalCauseName",
                    "isIconColumn": False
                },
                {
                    "field": "prolongationType",
                    "title": "Пролонгация",
                    "width": 120,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "ProlongationType",
                    "isIconColumn": False
                },
                {
                    "field": "serviceManagers",
                    "title": "Сервис-менеджеры",
                    "width": 300,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "ServiceManagers",
                    "isIconColumn": False
                },
                {
                    "field": "projectManagers",
                    "title": "Менеджеры проекта",
                    "width": 300,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "ProjectManagers",
                    "isIconColumn": False
                },
                {
                    "field": "techManagers",
                    "title": "Технические менеджеры",
                    "width": 300,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "TechManagers",
                    "isIconColumn": False
                },
                {
                    "field": "documentumFileLink",
                    "title": "Ссылка на документ с ЕЦП",
                    "width": 300,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "DocumentumFileLink",
                    "isIconColumn": False
                },
                {
                    "field": "amount",
                    "title": "Сумма контракта в валюте документа",
                    "width": 280,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "Amount",
                    "isIconColumn": False
                },
                {
                    "field": "amountRub",
                    "title": "Сумма контракта в рублях",
                    "width": 200,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "AmountRub",
                    "isIconColumn": False
                },
                {
                    "field": "firm.name",
                    "title": "Фирма",
                    "width": 90,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": "firm.displayName",
                    "excelExportName": "FirmName",
                    "isIconColumn": False
                },
                {
                    "field": "directions",
                    "title": "Направления договора",
                    "width": 300,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "Directions",
                    "isIconColumn": False
                },
                {
                    "field": "directors",
                    "title": "Директор Клиента",
                    "width": 300,
                    "sortable": False,
                    "isVisible": True,
                    "displayFieldName": None,
                    "excelExportName": "DirectorName",
                    "isIconColumn": False
                },
                {
                    "field": "organization.currentClientSegment",
                    "title": "Сегмент клиента ДИРС2",
                    "width": 200,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "CurrentClientSegment",
                    "isIconColumn": False
                },
                {
                    "field": "organization.clientCardIB.SegmentManual",
                    "title": "Сегмент клиента ИБ1",
                    "width": 200,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": "currentClientSegmentIB",
                    "excelExportName": "CurrentClientSegmentIB",
                    "isIconColumn": False
                },
                {
                    "field": "servicePlans",
                    "title": "Программы обслуживания",
                    "width": 200,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "ServicePlans",
                    "isIconColumn": False
                },
                {
                    "field": "subAgreements",
                    "title": "Субподрядные договоры",
                    "width": 200,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "SubAgreements",
                    "isIconColumn": False
                },
                {
                    "field": "otherAgreementForCU.crocCode",
                    "title": "Договор учета КЕ",
                    "width": 200,
                    "sortable": True,
                    "isVisible": False,
                    "displayFieldName": "otherAgreementForCU.displayName",
                    "excelExportName": "OtherAgreementForCU",
                    "isIconColumn": False
                },
                {
                    "field": "isOtherClientAgreements",
                    "title": "По Клиенту есть договоры других направлений",
                    "width": 200,
                    "sortable": False,
                    "isVisible": False,
                    "displayFieldName": None,
                    "excelExportName": "IsOtherClientAgreements",
                    "isIconColumn": False
                }
            ],
            "filter": {
                "directions": {
                    "IsListSearch": True,
                    "ItemList": ["DIR000094"]
                },
                "negativeFilters": [],
                "onlyService": False,
                "gridState": {
                    "skip": 0,
                    "take": 80,
                    "sort": []
                }
            }
        }

    async def _refresh_token(self) -> bool:
        """Запрашивает новый access-токен через Client Credentials Flow асинхронно."""
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid"  # Уточните scope у администратора ADFS
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    ssl=False
                ) as response:
                    response.raise_for_status()
                    token_data = await response.json()
                    print(token_data)
                    self.access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 3600)  # По умолчанию 1 час
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    self.robot_logger.success("Новый токен получен.")
                    return True
        except aiohttp.ClientError as e:
            self.robot_logger.critical(f"Ошибка получения токена: {e}")
            return False

    async def _check_token_status(self) -> bool:
        """Проверяет статус токена и обновляет его, если необходимо."""
        if self.access_token:
            self.robot_logger.debug("Токен валиден.")
            return True

        self.robot_logger.debug("Токен отсутствует или истек, обновляем.")
        return await self._refresh_token()

    async def _get_headers(self) -> dict:
        """Формирует заголовки с токеном."""
        if not await self._check_token_status():
            self.robot_logger.critical("Не удалось получить валидный токен.")
            raise ValueError("Токен недоступен")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.headers["User-Agent"],
            "Content-Type": "application/json"
        }

    async def _post(self, url: str) -> Optional[dict]:
        """Отправляет асинхронный POST-запрос с OAuth2 Bearer-токеном."""
        try:
            headers = await self._get_headers()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    headers=headers,
                    json=self.params,
                    ssl=False
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            if e.status == 401:
                self.robot_logger.debug("Токен недействителен, пытаемся обновить.")
                self.access_token = None  # Сбрасываем токен
                if await self._refresh_token():
                    return await self._post(url)  # Повторяем запрос с новым токеном
            self.robot_logger.error(f"Ошибка при выполнении запроса: {e}")
            return None

    def _decode_and_process_file(self, encoded_data: str, output_path: Path) -> None:
        """Декодирует файл, извлекает уникальные активные коды и сохраняет их в Excel."""
        try:
            decoded_data = base64.b64decode(encoded_data)
            with pd.ExcelFile(BytesIO(decoded_data)) as xls:
                df = pd.read_excel(xls, sheet_name=0)

            codes = {
                active[1:9] for active in df.get('Активность', [])
                if isinstance(active, str) and len(active) > 8
            }

            wb = Workbook()
            ws = wb.active
            ws['A1'] = 'КОД ПРОЕКТА'
            for ind, code in enumerate(codes, start=2):
                ws[f'A{ind}'] = code

            wb.save(output_path)
            self.robot_logger.success('Договора из СУС обновлены.')
        except Exception as e:
            self.robot_logger.error(f"Ошибка при декодировании и обработке файла: {e}")

    async def parsing_active(self, sys_dir: Path) -> None:
        """Выполняет асинхронный парсинг активных кодов и сохраняет их в файл Excel."""
        self.robot_logger.debug('Процесс обновления договоров через СУС')
        fulldir = sys_dir / 'Договора.xlsx'
        response_data = await self._post(self.url)
        if not response_data:
            return

        self._decode_and_process_file(
            response_data['data']['fileContent'],
            fulldir,
        )