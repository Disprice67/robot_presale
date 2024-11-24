from sqlalchemy import delete, Table, inspect
from sqlalchemy.orm import Session
from infrastructure.database.orm.models import AbstractTable, FileMetadata
from core import IDatabaseRepository, EliminationFilter, IRobotLogger
from infrastructure.database.settings.db_settings import SQLAlchemySettings
import pandas as pd
from pathlib import Path
from sqlalchemy.ext.declarative import DeclarativeMeta
from typing import Optional
from datetime import datetime


class DatabaseRepository(IDatabaseRepository):
    def __init__(self, settings_aclhemy: SQLAlchemySettings, robot_logger: IRobotLogger) -> None:
        self.session = settings_aclhemy.session_factory
        self.engine = settings_aclhemy.engine
        self.robot_logger = robot_logger

        if not self._is_database_initialized():
            self._create_all_tables()

        self._ensure_all_tables_exist()

    def _is_database_initialized(self) -> bool:
        """Проверяет, инициализирована ли база данных (существуют ли таблицы)."""
        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()
        if existing_tables:
            self.robot_logger.debug('База данных уже инициализирована.')
            return True
        self.robot_logger.info("База данных не найдена. Создаем новую.")
        return False

    def _ensure_all_tables_exist(self) -> None:
        """
        Проверяет наличие всех таблиц, определённых в модели, и создаёт отсутствующие.
        """
        try:
            inspector = inspect(self.engine)
            existing_tables = set(inspector.get_table_names())
            all_tables = set(AbstractTable.metadata.tables.keys())

            missing_tables = all_tables - existing_tables
            if missing_tables:
                self.robot_logger.info(f"Отсутствующие таблицы: {missing_tables}. Создаём их...")
                for table_name in missing_tables:
                    try:
                        table = AbstractTable.metadata.tables[table_name]
                        table.create(self.engine)
                        self.robot_logger.success(f"Таблица '{table_name}' успешно создана.")
                    except Exception as e:
                        self.robot_logger.error(f"Ошибка при создании таблицы '{table_name}': {e}")
                self.robot_logger.success("Все отсутствующие таблицы успешно обработаны.")
            else:
                self.robot_logger.debug("Все таблицы уже существуют. Ничего не требуется создавать.")
        except Exception as e:
            self.robot_logger.error(f"Ошибка при проверке или создании таблиц: {e}")

    def get_all_tables(self) -> list[str]:
        return list(AbstractTable.metadata.tables.keys())[1:]

    def _get_model_class_by_table_name(self, table_name: str) -> Optional[type[DeclarativeMeta]]:
        """Получить ORM-класс по имени таблицы, используя рефлексию SQLAlchemy."""
        for cls in AbstractTable.__subclasses__():
            if cls.__table__.name == table_name:
                return cls
        return None

    def update_table(self, event) -> None:
        file_path = Path(event.src_path)
        table = AbstractTable.metadata.tables.get(file_path.parent.name)
        data = self._get_data_exl(table, file_path)
        self.robot_logger.info(f'Начинаем обновление {table.name}')
        if data:
            with self.session.begin() as session:
                session.execute(delete(table))
                self._insert_data(session, table, data)
                self._update_metadata(session, file_path)

    def _create_all_tables(self) -> None:
        AbstractTable.metadata.create_all(bind=self.engine)
        self.robot_logger.success("Таблицы успешно созданы или уже существуют.")

    def _column_validate(self, obj: Table, columns: list[str]) -> bool:
        """Check if the specified columns exist in the object."""
        obj_column = [column.name for column in obj.columns[:-1]]
        return set(obj_column).issubset(columns)

    def _get_data_exl(self, obj: Table, path: Path):
        try:
            col_lower = pd.read_excel(path, nrows=0).columns.tolist()
            col_upper = [col.upper() for col in col_lower]
            if self._column_validate(obj, col_upper):
                data = pd.read_excel(path, na_filter=False).to_dict('records')
                return data
            else:
                self.robot_logger.error(f'Валидация названия столбцов не пройдена {obj}')
                self.robot_logger.error(f'Book: {col_upper} Table: {obj.columns[:-1]}')
        except Exception as e:
            self.robot_logger.error(f'Ошибка чтения файла для загрузки в БД {e}')

    def _insert_data(self, session: Session, table: Table, data: list[dict]):
        """insert_data."""
        for item in data:
            obj_table = self._obj_create(table, item)
            if obj_table:
                try:
                    session.add(obj_table)
                    session.flush()
                except Exception as e:
                    session.rollback()
                    self.robot_logger.error(f'Не удалось добавить объект в {table.name} {obj_table}')
                    self.robot_logger.error(f'{e}')
                    continue
        self.robot_logger.success('Данные записаны в БД.')

    def _obj_create(self, table: Table, item: dict): # Добавить аннотацию
        """Создание объекта таблицы из данных."""
        item = {k.upper(): v for k, v in item.items()}
        obj_instance = self._get_model_class_by_table_name(table.name)()
        try:
            for attr in obj_instance.__mapper__.attrs:
                attr_name = attr.expression.name
                if attr_name in item:
                    value = item[attr_name]
                    if not attr.columns[0].nullable:
                        if not isinstance(value, str) or not value:
                            return
                        if table.name == 'Запасные Категории':
                            value = EliminationFilter.filter(value)
                        else:
                            value = value.replace(' ', '').upper()
                    setattr(obj_instance, attr.key, value)
            return obj_instance
        except Exception as e:
            self.robot_logger.error(f'Ошибка создания объекта для БД {e}')
            return

    def _update_metadata(self, session: Session, file_path: Path, status: str = 'updated') -> None:

        filename = file_path.name
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        model_type = file_path.parent.name
        try:
            metadata = session.query(FileMetadata).filter_by(filename=filename).first()
            if metadata:
                metadata.file_path = str(file_path)
                metadata.last_modified = last_modified
                metadata.status = status
                metadata.model_type = model_type
            else:
                metadata = FileMetadata(
                    model_type=model_type,
                    filename=filename,
                    file_path=str(file_path),
                    last_modified=last_modified,
                    status=status
                )
                session.add(metadata)
            self.robot_logger.success(f'Объект таблицы {model_type} обновлен.')
            self.robot_logger.success(f'{metadata}')
        except Exception as e:
            self.robot_logger.error(f"Ошибка при обновлении метаданных файла: {e}")