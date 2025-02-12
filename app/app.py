from core import InputData, EliminationFilter, ExceptionGenerator, Economics
from services import (DatabaseService,
                      ORMService,
                      EbayService,
                      EmailService,
                      HuaweiService,
                      MonitorFilesService,
                      ExcelHandlerService,
                      SYSHandlerService,
                      DataService)

from infrastructure import (SQLAlchemySettings,
                            DatabaseRepository,
                            FileEventHandler,
                            MonitorFiles,
                            SYSHandler,
                            ParsingHuawei,
                            ParsingSYS,
                            EbayCom,
                            Email,
                            ORMQuary,
                            ExcelHandler,
                            RobotLogger)

from settings.config import Settings
from pathlib import Path
import os
import time

class AppCoordinator:
    def __init__(
            self,
            settings: Settings,
            base_dir: Path,
            buffer_dir: Path,
            network_disk_dir: Path,
            sql_aclhemy_settings: SQLAlchemySettings,
            robot_logger: RobotLogger
    ):
        self._database_service = None
        self._orm_service = None
        self._ebay_service = None
        self._email_service = None
        self._huawei_service = None
        self._monitor_files_service = None
        self._excel_handler_service = None
        self._sys_handler_service = None
        self._data_service = None

        self._settings = settings
        self._sql_alchemy_settings = sql_aclhemy_settings
        self._robot_logger = robot_logger
        self._base_dir = base_dir
        self._buffer_dir = buffer_dir
        self._network_disk_dir = network_disk_dir
        self._buffer_in = buffer_dir / 'in'

    @property
    def database_service(self,) -> DatabaseService:
        if self._database_service is None:
            self._database_service = DatabaseService(
                DatabaseRepository(
                    self._sql_alchemy_settings,
                    self._robot_logger
                )
            )
        return self._database_service

    @property
    def orm_service(self) -> ORMService:
        if self._orm_service is None:
            self._orm_service = ORMService(
                ORMQuary(
                    self._sql_alchemy_settings,
                    self._robot_logger
                )
            )
        return self._orm_service

    @property
    def ebay_service(self) -> EbayService:
        if self._ebay_service is None:
            self._ebay_service = EbayService(
                EbayCom(
                    self._settings.ebay,
                    self._robot_logger
                )
            )
        return self._ebay_service

    @property
    def email_service(self) -> EmailService:
        if self._email_service is None:
            self._email_service = EmailService(
                Email(
                    self._settings.outlook,
                    self._buffer_in,
                    self._robot_logger
                )
            )
        return self._email_service

    @property
    def huawei_service(self) -> HuaweiService:
        if self._huawei_service is None:
            self._huawei_service = HuaweiService(
                ParsingHuawei(
                    self._settings.huaweidata,
                    self._settings.huaweidata.header,
                    self._robot_logger
                )
            )
        return self._huawei_service

    @property
    def monitor_files_service(self) -> MonitorFilesService:
        if self._monitor_files_service is None:
            self._monitor_files_service = MonitorFilesService(
                MonitorFiles(
                    self.database_service,
                    self._robot_logger,
                    FileEventHandler(
                        self.database_service,
                        self._robot_logger
                    )
                )
            )
        return self._monitor_files_service

    @property
    def excel_handler_service(self) -> ExcelHandlerService:
        if self._excel_handler_service is None:
            self._excel_handler_service = ExcelHandlerService(
                ExcelHandler(
                    self._buffer_dir,
                    self._robot_logger
                )
            )
        return self._excel_handler_service

    @property
    def sys_handler_service(self) -> SYSHandlerService:
        if self._sys_handler_service is None:
            self._sys_handler_service = SYSHandlerService(
                SYSHandler(
                    ParsingSYS(
                        self._settings.sysdata,
                        self._settings.huaweidata.header,
                        self._robot_logger
                    ),
                    self._network_disk_dir,
                    self._robot_logger
                )
            )
        return self._sys_handler_service

    @property
    def data_service(self,) -> DataService:
        if self._data_service is None:
            self._data_service = DataService(
                EliminationFilter(
                    self._robot_logger
                ),
                ExceptionGenerator(
                    ParsingHuawei(
                        self._settings.huaweidata,
                        self._settings.huaweidata.header,
                        self._robot_logger
                    ),
                    self._robot_logger,
                ),
                Economics(
                    self._robot_logger
                )
            )
        return self._data_service

    def _monitor_files(self):
        """Мониторинг файлов в указанных каталогах."""
        directories_to_monitor = [
            self._network_disk_dir / table
            for table in self.database_service.get_all_tables()
            ]
        return self.monitor_files_service.start_monitoring(directories_to_monitor)

    def _handle_excel(self, file_path: Path) -> list[InputData]:
        """Обработка Excel-файла."""
        return self.excel_handler_service.read_excel(file_path)

    def _collection_data(self, input_data: list[InputData]):
        data_generate_dict_list = [data.dict(by_alias=True) for data in input_data]
        for mass in data_generate_dict_list:
            for index, item in enumerate(mass.get('input_data')):
                part_number = item.get('P/N')
                vendor = item.get('ВЕНДОР')
                comment = item.get('ОПИСАНИЕ')

                filter_comment = self.data_service.elimination().filter(comment)

                exc_part_numbers = self.data_service.generate_exceptions(
                    item,
                    part_number,
                    vendor,
                )
                self.orm_service.directory_books_query(item, exc_part_numbers)
                self.orm_service.category_query(item, part_number, filter_comment)
                self.data_service.costs_by_category(item)

                category = item.get('КАТЕГОРИЯ')
                if category not in ('LIC-1', 'SOFT-1', 'MSCL'):
                    self.ebay_service.searchebay(
                        item,
                        part_number,
                        vendor,
                        self.data_service.elimination()
                    )
        return data_generate_dict_list

    def _process_file(self, file_path):
        """Обрабатываем один файл: извлекаем данные, записываем и отправляем email."""
        try:
            _input_data = self._handle_excel(file_path)
            if not _input_data:
                self._robot_logger.info(f"No data found in {file_path}")
                return False

            _data_collection = self._collection_data(_input_data)
            for data in _data_collection:
                if self.excel_handler_service.write_to_excel(data, file_path.name):
                    self.email_service.send_email(
                        self.excel_handler_service.get_output_file(file_path.name),
                        data['sheet_name']
                    )
            return True
        except Exception as e:
            self._robot_logger.error(f"Error processing file {file_path}: {e}")
            return False

    def _process_email_batch(self):
        """Обработка пакета email, включая загрузку и обработку файлов."""
        if self.email_service.download_attachments():
            self._robot_logger.info("Email batch processed successfully")
            for file_path in self.email_service.get_file_list():
                self._process_file(file_path)
                self._robot_logger.verify_logs_and_alert(file_path)
                time.sleep(3)
                file_path.unlink()
            self.email_service.remove_sender_email()
            self.email_service.clear_file_list()

    def _monitor_and_process(self):
        """Запуск мониторинга файлов и обработки email."""
        self._monitor_files()
        self.sys_handler_service.start_monitoring()
        self._robot_logger.verify_logs_and_alert()

        while True:
            try:
                self._process_email_batch()
                time.sleep(10)
            except Exception as e:
                self._robot_logger.critical(f"Unexpected error: {e}")
                self._robot_logger.verify_logs_and_alert()
                time.sleep(10)

    def robot_process(self):
        """Запуск работы робота."""
        try:
            self._robot_logger.clear_log_file()
            self._monitor_and_process()
        except Exception as e:
            self._robot_logger.critical(f"Fatal error in robot process: {e}")
            self._robot_logger.verify_logs_and_alert()
            time.sleep(100)
