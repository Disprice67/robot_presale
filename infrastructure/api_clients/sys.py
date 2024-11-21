import requests
from requests_ntlm import HttpNtlmAuth
from openpyxl import Workbook
import base64
import pandas as pd
from typing import Optional
from pathlib import Path
from settings.config import SysData, HuaweiHeader
from core import IRobotLogger


class ParsingSYS:
    TAKE = 80

    def __init__(self, settings_sys: SysData, header: HuaweiHeader, robot_logger: IRobotLogger):
        self.url = settings_sys.url_sys_agreements
        self.username = settings_sys.sys_username
        self.password = settings_sys.sys_password
        self.robot_logger = robot_logger
        self.headers = {'User-Agent': header.user_agent}
        self.params = {
            'columns': {"activity": 'true'},
            'filter': {
                "code": "",
                "additionalCrocCode": "",
                "serviceDirections": ["DIR000094"],
                "negativeFilters": [],
                "gridState": {
                    "group": [],
                    "sort": [],
                    "take": self.TAKE
                }
            }
        }

    def _post(self, url: str) -> Optional[dict]:
        """Отправляет POST-запрос и возвращает JSON-данные при успешном ответе."""
        try:
            response = requests.post(
                url=url,
                headers=self.headers,
                json=self.params,
                verify=False,
                auth=HttpNtlmAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.robot_logger.error(f"Ошибка при выполнении запроса: {e}")
            return None

    def _decode_and_process_file(self, encoded_data: str, output_path: Path) -> None:
        """Декодирует файл, извлекает активные коды и сохраняет их в Excel."""
        try:
            decoded_data = base64.b64decode(encoded_data)
            with pd.ExcelFile(decoded_data) as xls:
                df = pd.read_excel(xls, sheet_name=0)
            # убрать дубли
            codes = [
                active[1:9] for active in df.get('Активность', [])
                if isinstance(active, str) and len(active) > 8
            ]
            wb = Workbook()
            ws = wb.active
            ws['A1'] = 'КОД ПРОЕКТА'
            for ind, code in enumerate(codes, start=2):
                ws[f'A{ind}'] = code

            wb.save(output_path)
        except Exception as e:
            self.robot_logger.error(f"Ошибка при декодировании и обработке файла: {e}")

    def parsing_active(self, sys_dir: Path) -> None:
        """Выполняет парсинг активных кодов и сохраняет их в файл Excel."""
        self.robot_logger.debug('Процесс обновления договоров через СУС')
        fulldir = sys_dir / 'Договора.xlsx'
        response_data = self._post(self.url)
        if not response_data:
            return

        self._decode_and_process_file(
            response_data['data']['fileContent'],
            fulldir,
        )
