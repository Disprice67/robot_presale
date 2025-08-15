from core import InputData, PartNumberFilter, ExceptionGenerator, Economics
from services import (DatabaseService,
                      ORMService,
                      EmailService,
                      HuaweiService,
                      MonitorFilesService,
                      ExcelHandlerService,
                      SYSHandlerService,
                      DataService,
                      ExternalSearchService)

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
                            RobotLogger,
                            BouzParser,
                            NagParser,
                            YandexMarketParser)

from settings.config import Settings
from pathlib import Path
import os
import time
import asyncio
import aiofiles.os


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
        self._external_search_service = None
        self._email_service = None
        self._huawei_service = None
        self._monitor_files_service = None
        self._excel_handler_service = None
        self._sys_handler_service = None
        self._data_service = None
        self._bouz_service = None

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
                    self._robot_logger,
                    PartNumberFilter(self._robot_logger)
                )
            )
        return self._database_service

    @property
    def orm_service(self) -> ORMService:
        if self._orm_service is None:
            self._orm_service = ORMService(
                ORMQuary(
                    self._sql_alchemy_settings,
                    self._robot_logger,
                    PartNumberFilter(self._robot_logger)
                )
            )
        return self._orm_service

    @property
    def external_search_service(self) -> ExternalSearchService:
        if self._external_search_service is None:
            self._external_search_service = ExternalSearchService(
                bouz=BouzParser(self._robot_logger),
                nag=NagParser(self._robot_logger),
                ebay=EbayCom(self._settings.ebay, self._robot_logger),
                yandex_market=YandexMarketParser(self._robot_logger),
                robot_logger=self._robot_logger,
                usd_rate=100
            )
        return self._external_search_service

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
                part_number_filter=PartNumberFilter(
                    self._robot_logger
                ),
                exception_generator=ExceptionGenerator(
                    ParsingHuawei(
                        self._settings.huaweidata,
                        self._settings.huaweidata.header,
                        self._robot_logger
                    ),
                    self._robot_logger
                ),
                economics=Economics(
                    self._robot_logger
                )
            )
        return self._data_service

    async def _monitor_files(self):
        """Мониторинг файлов в указанных каталогах."""
        directories_to_monitor = [
            self._network_disk_dir / table
            for table in await self.database_service.get_all_tables()
        ]
        self.monitor_files_service.start_monitoring(directories_to_monitor)

    def _handle_excel(self, file_path: Path) -> list[InputData]:
        """Обработка Excel-файла (синхронная)."""
        return self.excel_handler_service.read_excel(file_path)

    async def _collection_data(self, input_data: list[InputData]):
        data_generate_dict_list = [data.dict(by_alias=True) for data in input_data]

        async def process_item(item):
            try:
                part_number = item.get('P/N')
                vendor = item.get('ВЕНДОР')
                comment = item.get('ОПИСАНИЕ')
                normalized_comment = self.data_service._part_number_filter.normalize_part_number(comment)
                normalized_part_number = self.data_service._part_number_filter.normalize_part_number(part_number)

                exc_part_numbers = await self.data_service.generate_exceptions(
                    item, normalized_part_number, vendor
                )

                await self.orm_service.directory_books_query(item, exc_part_numbers, normalized_comment)

                self.data_service.costs_by_category(item)

                category = item.get('КАТЕГОРИЯ')
                if category not in ('LIC-1', 'SOFT-1', 'MSCL'):
                    await self.external_search_service.search(
                        item, part_number, vendor, self.data_service._part_number_filter
                    )
            except Exception as e:
                self._robot_logger.error(f"Error processing item {item.get('P/N')}: {e}")

        tasks = [process_item(item) for mass in data_generate_dict_list for item in mass.get('input_data')]
        await asyncio.gather(*tasks, return_exceptions=False)

        return data_generate_dict_list

    async def _process_file(self, file_path: Path):
        """Обрабатываем один файл: извлекаем данные, записываем и отправляем email."""
        try:
            _input_data = self._handle_excel(file_path)
            if not _input_data:
                self._robot_logger.info(f"No data found in {file_path}")
                return False
            _data_collection = await self._collection_data(_input_data)
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

    async def _process_email_batch(self):
        """Обработка пакета email, включая загрузку и обработку файлов."""
        if self.email_service.download_attachments():
            self._robot_logger.info("Email batch processed successfully")
            for file_path in self.email_service.get_file_list():
                await self._process_file(file_path)
                self._robot_logger.verify_logs_and_alert(file_path)
                await asyncio.sleep(3)
                await aiofiles.os.unlink(file_path)
            self.email_service.clear_file_list()

    async def _monitor_and_process(self):
        """Запуск мониторинга файлов и обработки email."""
        monitor_task = asyncio.create_task(self._monitor_files())
        # sys_monitor_task = asyncio.create_task(self.sys_handler_service.start_monitoring())
        self._robot_logger.verify_logs_and_alert()

        while True:
            try:
                await self._process_email_batch()
                await asyncio.sleep(10)
            except Exception as e:
                self._robot_logger.critical(f"Unexpected error: {e}")
                self._robot_logger.verify_logs_and_alert()
                await asyncio.sleep(10)

    async def robot_process(self):
        """Запуск работы робота."""
        try:
            self._robot_logger.clear_log_file()
            await self._monitor_and_process()
        except Exception as e:
            self._robot_logger.critical(f"Fatal error in robot process: {e}")
            self._robot_logger.verify_logs_and_alert()
            await asyncio.sleep(100)

