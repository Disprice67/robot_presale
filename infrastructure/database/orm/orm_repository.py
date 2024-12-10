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
from core import IORMQuary, EliminationFilter, IRobotLogger
from typing import Optional


class AbstractQuaryORM:


    @staticmethod
    def search_by_part_number(quary: Query, obj_table: DeclarativeMeta, part_number: str, session: Session) -> Optional[dict[str, any]]:
        """
        Выполняет поиск по точному, неполному и обратному соответствию.
        :param query: SQLAlchemy Query объект.
        :param obj_table: Таблица или модель SQLAlchemy для поиска.
        :param part_number: Строка для поиска.
        :param session: Активная сессия SQLAlchemy.
        :return: Результат в виде словаря или None, если ничего не найдено.
        """
        quary_exact = quary.filter(part_number == obj_table.part_number)
        quary_exact = quary_exact.add_columns(
            case(
                (
                    part_number == obj_table.part_number,
                    case(
                        (obj_table == aliased(ArchiveBook), getattr(obj_table, 'zip_values', None)),
                        else_=obj_table.part_number
                    )
                ),
                else_=None
            ).label('ЗИП')
        )

        result = session.execute(quary_exact).first()
        if result:
            return result._asdict()

        quary_in = quary.filter(obj_table.part_number.like(f"%{part_number}%"))
        quary_in = quary_in.add_columns(
            case(
                (
                    obj_table.part_number.like(f"%{part_number}%"),
                    case(
                        (obj_table == aliased(ArchiveBook), getattr(obj_table, 'zip_values', None)),
                        else_=obj_table.part_number
                    )
                ),
                else_=None
            ).label('ЗИП')
        )
        result = session.execute(quary_in).first()
        if result:
            result_dict = result._asdict()
            result_dict['match_type'] = 'partial'
            return result_dict

        quary_out = quary.filter(func.instr(part_number, obj_table.part_number))
        quary_out = quary_out.add_columns(
            case(
                (
                    func.instr(part_number, obj_table.part_number) > 0,
                    case(
                        (obj_table == aliased(ArchiveBook), getattr(obj_table, 'zip_values', None)),
                        else_=obj_table.part_number
                    )
                ),
                else_=None
            ).label('ЗИП')
        )
        result = session.execute(quary_out).first()
        if result:
            result_dict = result._asdict()
            result_dict['match_type'] = 'partial'
            return result_dict
        return None

    @staticmethod
    def quaryes(quary, obj_table: DeclarativeMeta, keys: list[str], session: Session):
        """Цикл по part_number для выполнения поиска"""
        for part_number in keys:
            result = AbstractQuaryORM.search_by_part_number(
                quary, obj_table, part_number, session
            )
            if result:
                return result


class CodeBookRepository(AbstractQuaryORM):
    @staticmethod
    def get_items_by_keys(session: Session, keys: list[str]):
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
        return AbstractQuaryORM.quaryes(query, c, keys, session)



class PurchaseWantRepository(AbstractQuaryORM):
    @staticmethod
    def get_items_by_keys(session: Session, keys: list[str]):
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
        return AbstractQuaryORM.quaryes(quary, p, keys, session)


class PurchaseBuyRepository(AbstractQuaryORM):
    @staticmethod
    def get_items_by_keys(session: Session, keys: list[str]):
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
        return AbstractQuaryORM.quaryes(quary, p, keys, session)


class ArchiveBookRepository(AbstractQuaryORM):
    @staticmethod
    def get_items_by_keys(session: Session, keys: list[str]):
        a = aliased(ArchiveBook)
        s = aliased(Status)
        ac = aliased(AgreementsCollision)
        quary = select(
            a.cost_of_zip.label('$, СТОИМОСТЬ ЗАКУПКИ ЗИП'),
            a.dtk_service.label('ДТК Сервис (КОММЕНТАРИИ ИНЖЕНЕРОВ)'),
            a.appointment.label('НАЗНАЧЕНИЕ'),
            a.project_code.label('№ ЗАПРОСА'),
            func.sum(a.amount).label('QTY ИЗ АРХИВОВ'),
            literal('Архив').label('ГДЕ НАШЛИ')
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
        return AbstractQuaryORM.quaryes(quary, a, keys, session)

    @staticmethod
    def select_qty(session: Session, key: str):
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
        result = session.execute(quarys).first()
        if result:
            return result._asdict()


class CollisionRepository:
    @staticmethod
    def get_items_by_keys(session: Session, comment: str):
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
        result = session.execute(query).first()
        if result:
            return result._asdict()


class CategoryRepository:
    @staticmethod
    def get_items_by_keys(session: Session, key: str):
        m = aliased(MainCategory)
        s = aliased(SecondCategory)
        quary = select(
            m.category.label('КАТЕГОРИЯ'),
            m.repair.label('РЕМОНТ'),
            m.time.label('ТРУДОЗАТРАТЫ'),
        ).join(
            s, m.category == s.category
        ).filter(
            func.instr(EliminationFilter.filter(key), s.letters) == 1,
        ).order_by(func.length(s.letters).desc()).limit(1)
        result = session.execute(quary).first()
        if result:
            return result._asdict()


class ChassisRepository:
    @staticmethod
    def get_items_by_keys(session: Session, key: str):
        c = aliased(Chassis)
        quary = select(
            c.part_number,
            c.power_unit,
            c.fan_unit,
            c.comment
        ).select_from(
            c
        ).filter(func.instr(c.part_number, key) == 1)
        print(key)
        result = session.execute(quary).first()
        if result:
            part_bp = result.power_unit
            part_fan = result.fan_unit
            comment = result.comment

            return {
                'ШАССИ': f"Шасси! БП - {part_bp}, FAN - {part_fan}, Комментарий - {comment}"
            }


class ORMQuary(IORMQuary):
    def __init__(self, settings_aclhemy: SQLAlchemySettings, robot_logger: IRobotLogger):
        self.session_factory = settings_aclhemy.session_factory
        self.robot_logger = robot_logger

    def _execute_repository_query(self, query_func, *args, **kwargs):
        """Обертка для выполнения запросов в репозиториях."""
        try:
            with self.session_factory() as session:
                return query_func(session, *args, **kwargs)
        except Exception as e:
            self.robot_logger.error(f"Ошибка выполнения запроса: {str(query_func)} {e}")
            return None

    def directory_books_query(self, item: dict, keys: list) -> None:
        """Основной процесс поиска данных и обновления элемента."""
        self.robot_logger.debug(f'Процесс поиска по directory_books {keys[0]}')

        quary_result = self._find_primary_data(keys)
        if quary_result:
            quary_result = self._merge_archive_data(quary_result, keys[0])
        else:
            quary_result = self._find_archive_data(keys)

        quary_result = self._merge_chassis_data(quary_result, keys[0])

        if quary_result:
            self._log_and_update_item(item, quary_result)

    def _find_primary_data(self, keys: list):
        """Поиск данных в основных репозиториях."""
        repositories = [
            CodeBookRepository.get_items_by_keys,
            PurchaseBuyRepository.get_items_by_keys,
            PurchaseWantRepository.get_items_by_keys
        ]
        for repo_method in repositories:
            result = self._execute_repository_query(repo_method, keys)
            if result:
                return result
        return None

    def _merge_archive_data(self, quary_result: dict, key: str) -> dict:
        """Объединяет результаты с данными из архива."""
        qty_result = self._execute_repository_query(ArchiveBookRepository.select_qty, key)
        if qty_result:
            quary_result.update(qty_result)
        return quary_result

    def _find_archive_data(self, keys: list):
        """Поиск данных в архиве."""
        return self._execute_repository_query(ArchiveBookRepository.get_items_by_keys, keys)

    def _merge_chassis_data(self, quary_result: dict, key: str):
        """Объединяет результаты с данными шасси."""
        chassis_result = self._execute_repository_query(ChassisRepository.get_items_by_keys, key)
        if chassis_result:
            if quary_result:
                quary_result.update(chassis_result)
            else:
                quary_result = chassis_result
        return quary_result

    def _log_and_update_item(self, item: dict, quary_result: dict):
        """Логирует результаты и обновляет элемент."""
        zip_result = quary_result.get('ЗИП')
        book_result = quary_result.get('Где нашли')
        self.robot_logger.info(f'Нашли {zip_result} в {book_result}')
        item.update(quary_result)


    def category_query(self, item: dict, key: str, comment: str):
        """category__query."""
        self.robot_logger.debug(f'Процесс поиска категории {key}')
        quary_result = {}
        if comment:
            collision_result = self._execute_repository_query(
                CollisionRepository.get_items_by_keys,
                comment
            )
            if collision_result:
                quary_result.update(collision_result)
        if not quary_result:
            category_result = self._execute_repository_query(
                CategoryRepository.get_items_by_keys, key
            )
            if category_result:
                quary_result.update(category_result)
            else:
                quary_result.update(
                    {
                        'РЕМОНТ': 6001,
                        'ТРУДОЗАТРАТЫ': 4,
                        'КАТЕГОРИЯ': 'EMPTY'
                    }
                )
        item.update(quary_result)
