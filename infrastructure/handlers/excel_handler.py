import pandas as pd
from pathlib import Path
from core import DataGenerate, InputData, IExcelHandler, IRobotLogger
from openpyxl import load_workbook
from typing import Optional
from openpyxl.utils.exceptions import InvalidFileException


class ExcelHandler(IExcelHandler):

    _formules = {
        'PRICE/USD': '=IF(T{row}="","",T{row}*2+S{row})',
        'СТОИМОСТЬ ДОСТАВКИ/USD': '=IF(T{row}="","",T{row}/2)',
        'СТ-ТЬ ЗИП С НУЛЯ*1,15': '=IF(T{row}="","",(T{row}*2+S{row})*1.15)',
        '10% ОТ РЫН.ЦЕНЫ': '=IF(U{row}="","",N{row}*E{row}*0.1)',
        'РУБ, СТОИМОСТЬ ПОДДЕРЖКИ': '=E{row}*F{row}',
        'HOURS': '=E{row}*G{row}'
    }

    def __init__(self, buffer: Path, robot_logger: IRobotLogger):
        self._buffer = buffer
        self.robot_logger = robot_logger

    @property
    def _sample_file(self,):
        return self._buffer / 'write_sample' / 'sample.xlsx'

    def get_output_file(self, filename: str):
        return self._buffer / 'out' / f'{filename}'

    def read_excel(self, file_path_in: Path) -> Optional[list[InputData]]:
        """get_data_input."""
        mass: list = []
        try:
            with pd.ExcelFile(file_path_in) as excel_file:
                sheetnames = excel_file.sheet_names
                for sheet in sheetnames:
                    if sheet not in ('Оценка рыночной стоимости', 'Для архива'):
                        df_excel = pd.read_excel(excel_file, sheet, na_filter=False)
                        df_excel.columns = df_excel.columns.str.upper()
                        records = df_excel.to_dict('records')
                        a_data = DataGenerate(input_data=records, sheet_name=sheet)
                        list.append(mass, a_data)
            file_path_in.unlink()  # Удаляем файл после завершения работы
            return mass
        except Exception as e:
            self.robot_logger.error(f'Ошибка при обработке/чтение файла Input_Excel {e}')
            return

    def write_to_excel(self, data: dict, filename: str):
        """Записывает данные в файл Excel с обработкой исключений и логированием."""
        try:
            wb = load_workbook(self._sample_file)
            ws = wb['Расчет']
        except FileNotFoundError:
            error_message = f"Файл-шаблон '{self._sample_file}' не найден."
            self.robot_logger.error(error_message)
            return
        except InvalidFileException:
            error_message = f"Файл-шаблон '{self._sample_file}' имеет недопустимый формат."
            self.robot_logger.error(error_message)
            return
        except KeyError:
            error_message = "Шаблон не содержит листа 'Расчет'."
            self.robot_logger.error(error_message)
            return

        try:
            row = 2
            columns = {cell.value: cell.column for cell in ws[1] if cell.value}

            if not isinstance(data, dict) or 'input_data' not in data:
                error_message = "Некорректная структура данных. Ожидался словарь с ключом 'input_data'."
                self.robot_logger.error(error_message)
                return

            for item in data['input_data']:
                if not isinstance(item, dict):
                    error_message = f"Неверный формат данных: элемент {item} должен быть словарем."
                    self.robot_logger.error(error_message)
                    return

                data_dict_upper = {key.upper(): value for key, value in item.items()}
                for key, value in data_dict_upper.items():
                    if key in columns:
                        col = columns[key]
                        ws.cell(row=row, column=col, value=value)

                for key, formula in self._formules.items():
                    if key in columns:
                        col = columns[key]
                        formula_with_row = formula.format(row=row)
                        ws.cell(row=row, column=col, value=formula_with_row)

                row += 1

            output_file = self.get_output_file(filename)
            wb.save(output_file)
            self.robot_logger.success(f"Файл '{filename}' успешно создан.")
            return True
        except Exception as e:
            error_message = f"Ошибка при обработке данных для файла '{filename}': {e}"
            self.robot_logger.error(error_message)
            return
