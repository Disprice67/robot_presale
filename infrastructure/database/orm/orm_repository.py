from sqlalchemy import select, func, case, literal
from sqlalchemy.orm import aliased, Session, Query
from .models import (Status,
                    PurchaseBuy,
                    PurchaseWant,
                    MainCategory,
                    SecondCategory,
                    Collision,
                    CodeBook,
                    ArchiveBook,
                    Chassis,
                    Agreements,
                    AgreementsCollision)

from sqlalchemy.ext.declarative import DeclarativeMeta
from infrastructure.database.settings.db_settings import SQLAlchemySettings
from sqlalchemy.ext.asyncio import AsyncSession
from core import IORMQuary, IPartNumberFilter, IRobotLogger
from typing import Optional, Any


class AbstractQuaryORM:
    @staticmethod
    async def search_by_part_number(query, obj_table: DeclarativeMeta, part_number: str,
                                   session: AsyncSession, part_number_filter: IPartNumberFilter) -> Optional[dict]:
        normalized_column = func.upper(
            func.regexp_replace(obj_table.part_number, r'[^A-Za-zА-Яа-я0-9]', '')
        )
        query_exact = query.filter(part_number == normalized_column)
        query_exact = query_exact.add_columns(
            case(
                (
                    part_number == normalized_column,
                    case(
                        (obj_table._aliased_insp.mapper.class_ is ArchiveBook, getattr(obj_table, 'zip_values', None)),
                        else_=obj_table.part_number
                    )
                ),
                else_=None
            ).label('ЗИП')
        )
        result = (await session.execute(query_exact)).first()
        if result:
            return result._asdict()

        query_in = query.filter(normalized_column.like(f"%{part_number}%"))
        query_in = query_in.add_columns(
            case(
                (
                    normalized_column.like(f"%{part_number}%"),
                    case(
                        (obj_table._aliased_insp.mapper.class_ is ArchiveBook, getattr(obj_table, 'zip_values', None)),
                        else_=obj_table.part_number
                    )
                ),
                else_=None
            ).label('ЗИП')
        )
        result = (await session.execute(query_in)).first()
        if result:
            result_dict = result._asdict()
            result_dict['MATCH_TYPE'] = {'ЗИП': True}
            return result_dict

        query_out = query.filter(func.instr(part_number, normalized_column))
        query_out = query_out.add_columns(
            case(
                (
                    func.instr(part_number, normalized_column) > 0,
                    case(
                        (obj_table._aliased_insp.mapper.class_ is ArchiveBook, getattr(obj_table, 'zip_values', None)),
                        else_=obj_table.part_number
                    )
                ),
                else_=None
            ).label('ЗИП')
        )
        result = (await session.execute(query_out)).first()
        if result:
            result_dict = result._asdict()
            result_dict['MATCH_TYPE'] = {'ЗИП': True}
            return result_dict
        return None

    @staticmethod
    async def queries(query, obj_table: DeclarativeMeta, keys: list[str], session: AsyncSession, part_number_filter: IPartNumberFilter):
        for part_number in keys:
            result = await AbstractQuaryORM.search_by_part_number(
                query, obj_table, part_number, session, part_number_filter
            )
            if result:
                return result


class CodeBookRepository(AbstractQuaryORM):
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, keys: list[str], part_number_filter: IPartNumberFilter):
        c = aliased(CodeBook)
        a = aliased(Agreements)
        ac = aliased(AgreementsCollision)
        query = select(
            c.appointment.label('НАЗНАЧЕНИЕ'),
            c.logical_accounting.label('СКЛАД'),
            func.max(c.cost_price).label('$, СТОИМОСТЬ ЗАКУПКИ ЗИП'),
            literal('Свод').label('ГДЕ НАШЛИ'),
        ).select_from(
            c
        ).join(
            a, func.instr(c.appointment, a.project_code) > 0
        ).join(
            ac, a.project_code != ac.project_code_collision
        ).group_by(
            c.part_number
        ).order_by(
            func.length(c.part_number).desc()
        ).filter(
            func.instr(c.appointment, a.project_code) > 0,
            a.project_code != ac.project_code_collision
        ).limit(1)
        return await AbstractQuaryORM.queries(query, c, keys, session, part_number_filter)


class PurchaseWantRepository(AbstractQuaryORM):
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, keys: list[str], part_number_filter: IPartNumberFilter):
        p = aliased(PurchaseWant)
        engineer_comments = case(
            (
                p.buy_customized.isnot(None),
                'Хотим купить под ' + p.buy_customized + 'по цене' + p.assessed_value
            ),
            else_='Хотим купить под ' + p.client + 'по цене' + p.assessed_value
            ).label('ДТК СЕРВИС (КОММЕНТАРИИ ИНЖЕНЕРОВ)')

        quary = select(
            func.max(p.amount_of_purchase.label('$, СТОИМОСТЬ ЗАКУПКИ ЗИП')),
            p.shop.label('НАЗНАЧЕНИЕ'),
            literal('Закупка Хотим').label('ГДЕ НАШЛИ'),
            engineer_comments
        ).select_from(
            p
        ).order_by(
            func.length(p.part_number).desc()
        ).group_by(p.part_number).limit(1)
        return await AbstractQuaryORM.queries(quary, p, keys, session, part_number_filter)


class PurchaseBuyRepository(AbstractQuaryORM):
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, keys: list[str], part_number_filter: IPartNumberFilter):
        p = aliased(PurchaseBuy)
        a = aliased(Agreements)
        ac = aliased(AgreementsCollision)
        quary = select(
            p.client.label('ДТК СЕРВИС (КОММЕНТАРИИ ИНЖЕНЕРОВ)'),
            p.appointment.label('НАЗНАЧЕНИЕ'),
            literal('Закупка Закупаем').label('ГДЕ НАШЛИ')
        ).select_from(
            p
        ).order_by(
            func.length(p.part_number).desc()
        ).join(
            a, func.instr(p.appointment, a.project_code) > 0
        ).join(
            ac, a.project_code != ac.project_code_collision
        ).filter(
            func.instr(p.appointment, a.project_code) > 0,
            a.project_code != ac.project_code_collision
        ).limit(1)
        return await AbstractQuaryORM.queries(quary, p, keys, session, part_number_filter)


class ArchiveBookRepository(AbstractQuaryORM):
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, keys: list[str], part_number_filter: IPartNumberFilter):
        a = aliased(ArchiveBook)
        s = aliased(Status)
        ac = aliased(AgreementsCollision)
        quary = select(
            a.cost_of_zip.label('$, СТОИМОСТЬ ЗАКУПКИ ЗИП'),
            a.dtk_service.label('ДТК Сервис (КОММЕНТАРИИ ИНЖЕНЕРОВ)'),
            a.appointment.label('НАЗНАЧЕНИЕ'),
            a.project_code.label('№ ЗАПРОСА'),
            func.sum(a.amount).label('QTY ИЗ АРХИВОВ'),
            literal('Архив').label('ГДЕ НАШЛИ'),
        ).select_from(
            a
        ).join(
            s, a.project_code == s.request_number
        ).join(
            ac, func.instr(a.appointment, ac.project_code_collision) == 0
        ).order_by(
            func.length(a.part_number).desc()
        ).filter(
            func.instr(a.appointment, ac.project_code_collision) == 0,
            s.status == 'отправлено',
            a.zip_values != None,
            a.zip_values != '-',
            a.zip_values != '0',
        ).group_by(a.part_number).limit(1)
        return await AbstractQuaryORM.queries(quary, a, keys, session, part_number_filter)

    @staticmethod
    async def select_qty(session: AsyncSession, key: str):
        a = aliased(ArchiveBook)
        s = aliased(Status)
        quary = select(
            func.sum(a.amount).label('QTY ИЗ АРХИВОВ'),
            a.project_code.label('№ ЗАПРОСА'),
        ).select_from(
            a
        ).join(
            s, a.project_code == s.request_number
        ).filter(
            func.lower(func.replace(s.status, " ", "")) == 'отправлено'
        ).group_by(a.part_number)

        quarys = quary.filter(key == a.part_number)
        result = (await session.execute(quarys)).first()
        if result:
            return result._asdict()

    @staticmethod
    async def select_category(session: AsyncSession, key: str):
        m = aliased(MainCategory)
        a = aliased(ArchiveBook)
        normalized_column = func.upper(
            func.regexp_replace(a.part_number, r'[^A-Za-zА-Яа-я0-9]', '')
        )
        quary = select(
            a.category.label('КАТЕГОРИЯ'),
            m.time.label('ТРУДОЗАТРАТЫ'),
            m.repair.label('РЕМОНТ')
        ).select_from(
            a
        ).join(
            m, a.category == m.category
        ).filter(
            a.category == m.category,
            normalized_column == key
        ).group_by(a.part_number)

        result = (await session.execute(quary)).first()
        if result:
            return result._asdict()

    @staticmethod
    async def select_category_partial(session: AsyncSession, key: str, part_number_filter: IPartNumberFilter):
        """
        Ищет категорию по неполному совпадению парт-номера с фильтром по длине и ранжированием.
        """
        a = aliased(ArchiveBook)
        m = aliased(MainCategory)

        key_length = len(key)
        min_length = int(key_length * 0.8)
        max_length = int(key_length * 1.2)
        normalized_column = func.upper(
            func.regexp_replace(a.part_number, r'[^A-Za-zА-Яа-я0-9]', '')
        )

        partial_query = select(
            a.category.label('КАТЕГОРИЯ'),
            m.time.label('ТРУДОЗАТРАТЫ'),
            m.repair.label('РЕМОНТ'),
            a.part_number,
            func.length(a.part_number).label('part_length')
        ).select_from(a).join(
            m, a.category == m.category
        ).filter(
            normalized_column.like(f'%{key}%'),
            func.length(normalized_column).between(min_length, max_length),
            a.category == m.category
        ).order_by(
            func.abs(func.length(a.part_number) - key_length)
        ).limit(10)

        partial_results = (await session.execute(partial_query)).fetchall()
        if partial_results:
            best_match = None
            best_score = 0
            for result in partial_results:
                result_dict = result._asdict()
                score = part_number_filter.calculate_similarity_score(key, result_dict['part_number'])
                if score > best_score:
                    best_score = score
                    best_match = result_dict
            if best_match and best_score >= 70:
                return best_match

        return None


class CollisionRepository:
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, comment: str):
        c = aliased(Collision)
        m = aliased(MainCategory)
        query = select(
            m.category.label('КАТЕГОРИЯ'),
            m.repair.label('РЕМОНТ'),
            m.time.label('ТРУДОЗАТРАТЫ')
        ).join(
            c, func.instr(func.lower(comment.replace(' ', '')),
                          func.lower(func.replace(c.description_content, " ", ""))) > 0
        ).filter(
            m.category == c.category,
        ).limit(1)
        result = (await session.execute(query)).first()
        if result:
            return result._asdict()


class CategoryRepository:
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, key: str):
        m = aliased(MainCategory)
        s = aliased(SecondCategory)
        normalized_column = func.upper(
            func.regexp_replace(s.letters, r'[^A-Za-zА-Яа-я0-9]', '')
        )
        quary = select(
            m.category.label('КАТЕГОРИЯ'),
            m.repair.label('РЕМОНТ'),
            m.time.label('ТРУДОЗАТРАТЫ'),
        ).join(
            s, m.category == s.category
        ).filter(
            func.instr(key, normalized_column) == 1,
        ).order_by(func.length(s.letters).desc()).limit(1)
        result = (await session.execute(quary)).first()
        if result:
            return result._asdict()


class ChassisRepository:
    @staticmethod
    async def get_items_by_keys(session: AsyncSession, key: str):
        c = aliased(Chassis)
        normalized_column = func.upper(
            func.regexp_replace(c.part_number, r'[^A-Za-zА-Яа-я0-9]', '')
        )
        quary = select(
            c.part_number,
            c.power_unit,
            c.fan_unit,
            c.comment
        ).select_from(
            c
        ).filter(func.instr(normalized_column, key) == 1)
        result = (await session.execute(quary)).first()
        if result:
            part_bp = result.power_unit
            part_fan = result.fan_unit
            comment = result.comment

            return {
                'ШАССИ': f"Шасси! БП - {part_bp}, FAN - {part_fan}, Комментарий - {comment}"
            }


class ORMQuary(IORMQuary):
    def __init__(self, settings_alchemy: SQLAlchemySettings, robot_logger: IRobotLogger, part_number_filter: IPartNumberFilter):
        self.session_factory = settings_alchemy.session_factory
        self.robot_logger = robot_logger
        self.part_number_filter = part_number_filter

    async def _execute_repository_query(self, query_func, *args, **kwargs):
        try:
            async with self.session_factory() as session:
                return await query_func(session, *args, **kwargs)
        except Exception as e:
            self.robot_logger.error(f"Ошибка выполнения запроса: {str(query_func)} {e}")
            return None

    async def directory_books_query(self, item: dict, keys: list, normalized_comment: str) -> None:
        """
        Выполняет поиск данных по парт-номерам через различные репозитории и обновляет item.
        Каждый источник обрабатывается отдельно, результаты логируются и добавляются в item.
        """
        self.robot_logger.debug(f"Процесс поиска по directory_books для ключей: {keys}")

        primary_result = await self._find_primary_data(keys)
        if primary_result:
            self._log_and_update_item(item, primary_result)

        archive_result = await self._find_archive_data(keys, True if primary_result else False)
        if archive_result:
            self._log_and_update_item(item, archive_result)

        category_result = await self._find_category(keys, normalized_comment)
        if category_result:
            self._log_and_update_item(item, category_result)

        chassis_result = await self._find_chassis_data(keys[0])
        if chassis_result:
            self._log_and_update_item(item, chassis_result)

    async def _find_primary_data(self, keys: list):
        repositories = [
            CodeBookRepository.get_items_by_keys,
            PurchaseBuyRepository.get_items_by_keys,
            PurchaseWantRepository.get_items_by_keys
        ]
        for repo_method in repositories:
            result = await self._execute_repository_query(repo_method, keys, self.part_number_filter)
            if result:
                self.robot_logger.debug(f"Найдены данные в {repo_method.__name__}: {result}")
                return result
        return None

    async def _find_archive_data(self, keys: list[str], primary_result: bool) -> Optional[dict[str, Any]]:
        """
        Ищет данные в ArchiveBook и добавляет информацию о количестве (QTY).
        """
        if not primary_result:
            archive_result = await self._execute_repository_query(
                ArchiveBookRepository.get_items_by_keys, keys, self.part_number_filter
            )
            if archive_result:
                self.robot_logger.debug(f"Найдены данные в ArchiveBook: {archive_result}")
                return archive_result
        else:
            qty_result = await self._execute_repository_query(ArchiveBookRepository.select_qty, keys[0])
            if qty_result:
                self.robot_logger.debug(f"Найдены qty в ArchiveBook: {qty_result}")
                return qty_result
        return None

    async def _find_chassis_data(self, key: str) -> Optional[dict[str, Any]]:
        """
        Ищет данные по шасси для указанного ключа.
        """
        return await self._execute_repository_query(ChassisRepository.get_items_by_keys, key)

    async def _find_category(self, keys: list[str], normalized_comment: str) -> Optional[dict[str, Any]]:
        """
        Ищет категорию в ArchiveBook (точное или частичное совпадение) или по комментарию/ключу.
        """
        async with self.session_factory() as session:
            for key in keys:
                exact_result = await ArchiveBookRepository.select_category(session, key)
                if exact_result:
                    self.robot_logger.debug(f"Найдена категория (точное совпадение) для {key}: {exact_result}")
                    return exact_result

            for key in keys:
                partial_result = await ArchiveBookRepository.select_category_partial(
                    session, key, self.part_number_filter
                )
                if partial_result:
                    self.robot_logger.debug(f"Найдена категория (частичное совпадение) для {key}: {partial_result}")
                    return partial_result

        if normalized_comment:
            comment_result = await self._execute_repository_query(
                CollisionRepository.get_items_by_keys, normalized_comment
            )
            if comment_result:
                self.robot_logger.debug(f"Найдена категория по комментарию: {comment_result}")
                return comment_result

        key_result = await self._execute_repository_query(CategoryRepository.get_items_by_keys, keys[0])
        if key_result:
            key_result['MATCH_TYPE'] = {'КАТЕГОРИЯ': True}
            self.robot_logger.debug(f"Найдена категория по ключу {keys[0]}: {key_result}")
            return key_result

        default_result = {
            'РЕМОНТ': 6001,
            'ТРУДОЗАТРАТЫ': 4,
            'КАТЕГОРИЯ': 'EMPTY'
        }
        self.robot_logger.debug(f"Категория не найдена, используются значения по умолчанию: {default_result}")
        return default_result

    def _log_and_update_item(self, item: dict, query_result: dict) -> None:
        """
        Логирует найденные данные и обновляет item.
        """
        zip_result = query_result.get('ЗИП')
        book_result = query_result.get('ГДЕ НАШЛИ', 'неизвестный источник')
        category = query_result.get('КАТЕГОРИЯ')
        if zip_result or category:
            log_message = f"Нашли данные: ЗИП={zip_result}, Категория={category} в {book_result}"
            self.robot_logger.success(log_message)
        item.update(query_result)
