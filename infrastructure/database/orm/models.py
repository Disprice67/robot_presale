from typing import Annotated, Optional, Union
from sqlalchemy.orm import as_declarative, mapped_column, declared_attr, Mapped
from datetime import datetime


intpk = Annotated[int, mapped_column(autoincrement=True, primary_key=True)]


@as_declarative()
class AbstractTable:

    __abstract__ = True

    id: Mapped[intpk]

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__doc__


class FileMetadata(AbstractTable):
    """Metadata"""
    model_type: Mapped[str] = mapped_column()
    filename: Mapped[str] = mapped_column(name='filename')
    file_path: Mapped[str] = mapped_column(name='file_path')
    last_modified: Mapped[datetime] = mapped_column(name='last_modified')
    status: Mapped[str] = mapped_column(name='status')

    def __repr__(self) -> str:
        return (f'FileMetadata(filename={self.filename}, file_path={self.file_path}, '
                f'last_modified={self.last_modified}, status={self.status})')


class Status(AbstractTable):
    """Статусы"""
    request_number: Mapped[str] = mapped_column(name='№ ЗАПРОСА')
    status: Mapped[Optional[str]] = mapped_column(name='СТАТУС')


class PurchaseBuy(AbstractTable):
    """Закупка Закупаем"""
    part_number: Mapped[str] = mapped_column(name='АРТИКУЛ')
    client: Mapped[Optional[str]] = mapped_column(name='КЛИЕНТ')
    appointment: Mapped[Optional[str]] = mapped_column(name='НАЗНАЧЕНИЕ')

    def __repr__(self) -> str:
        return (f'PurchaseBuy(part_number={self.part_number}, client={self.client}, '
                f'appointment={self.appointment})')


class PurchaseWant(AbstractTable):
    """Закупка Хотим"""
    part_number: Mapped[str] = mapped_column(name='P/N')
    client: Mapped[Optional[str]] = mapped_column(name='КЛИЕНТЫ')
    buy_customized: Mapped[Optional[str]] = mapped_column(name='ЗАКУПАЕМ ПОД ЗАКАЗЧИКА')
    amount_of_purchase: Mapped[Optional[str]] = mapped_column(name='СУММА СОВМЕСТНОЙ ЗАКУПКИ')
    shop: Mapped[Optional[str]] = mapped_column(name='МАГАЗИН')
    assessed_value: Mapped[Optional[str]] = mapped_column(name='ОЦЕНОЧНАЯ СТОИМОСТЬ')

    def __repr__(self) -> str:
        return (f'PurchaseWant(part_number={self.part_number}, client={self.client}, '
                f'buy_customized={self.buy_customized}, amount_of_purchase={self.amount_of_purchase}, '
                f'shop={self.shop}, assessed_value={self.assessed_value})')


class MainCategory(AbstractTable):
    """Основные Категории"""
    category: Mapped[Optional[str]] = mapped_column(name='КАТЕГОРИЯ')
    time: Mapped[Optional[float]] = mapped_column(name='ТЗ')
    repair: Mapped[Optional[int]] = mapped_column(name='РЕМОНТЫ')

    def __repr__(self) -> str:
        return f'MainCategory(category={self.category}, time={self.time}, repair={self.repair})'


class SecondCategory(AbstractTable):
    """Запасные Категории"""
    letters: Mapped[str] = mapped_column(name='МОДЕЛЬ НАЧИНАЕТСЯ С…')
    category: Mapped[Optional[str]] = mapped_column(name='КАТЕГОРИЯ СЛОЖНОСТИ ТЗ')

    def __repr__(self) -> str:
        return (f'SecondCategory(letters={self.letters})')


class Collision(AbstractTable):
    """Исключения"""
    description_content: Mapped[Optional[str]] = mapped_column(name='ОПИСАНИЕ ВКЛЮЧАЕТ')
    category: Mapped[Optional[str]] = mapped_column(name='КАТЕГОРИЯ СЛОЖНОСТИ ТЗ')

    def __repr__(self) -> str:
        return (f'Collision(description_content={self.description_content})')


class CodeBook(AbstractTable):
    """Свод"""
    part_number: Mapped[str] = mapped_column(name='PART #')
    appointment: Mapped[Optional[str]] = mapped_column(name='НАЗНАЧЕНИЕ')
    logical_accounting: Mapped[Optional[str]] = mapped_column(name='ЛОГИЧЕСКИЙ УЧЕТ')
    cost_price: Mapped[Optional[str]] = mapped_column(name='CЕБЕСТОИМОСТЬ ЕДИНИЦЫ БЕЗ НДС')

    def __repr__(self) -> str:
        return (f'CodeBook(part_number={self.part_number}, appointment={self.appointment}, '
                f'logical_accounting={self.logical_accounting}, cost_price={self.cost_price})')


class ArchiveBook(AbstractTable):
    """Архив"""
    part_number: Mapped[str] = mapped_column(name='P/N')
    cost_of_zip: Mapped[Optional[str]] = mapped_column(name='СТОИМОСТЬ ЗАКУПКИ ЗИП')
    zip_values: Mapped[Optional[str]] = mapped_column(name='ЗИП')
    dtk_service: Mapped[Optional[str]] = mapped_column(name='ДТК СЕРВИС')
    appointment: Mapped[Optional[str]] = mapped_column(name='НАЗНАЧЕНИЕ')
    amount: Mapped[Optional[str]] = mapped_column(name='КОЛ-ВО')
    project_code: Mapped[Optional[str]] = mapped_column(name='№ ЗАПРОСА')
    category: Mapped[Optional[str]] = mapped_column(name='КАТЕГОРИЯ')

    def __repr__(self) -> str:
        return (f'ArchiveBook(part_number={self.part_number}, cost_of_zip={self.cost_of_zip}, '
                f'zip_values={self.zip_values}, dtk_service={self.dtk_service}, '
                f'appointment={self.appointment}, amount={self.amount}, project_code={self.project_code}, '
                f'category={self.category}')


class Chassis(AbstractTable):
    """Шасси"""
    part_number: Mapped[str] = mapped_column(name='P/N', key='part_number')
    power_unit: Mapped[Optional[str]] = mapped_column(name='БП')
    fan_unit: Mapped[Optional[str]] = mapped_column(name='FAN')
    comment: Mapped[Optional[str]] = mapped_column(name='КОММЕНТАРИИ')

    def __repr__(self) -> str:
        return (f'Сhassis(part_number={self.part_number}, power_unit={self.power_unit}, '
                f'fan_unit={self.fan_unit}, comment={self.comment})')


class Agreements(AbstractTable):
    """Договора"""
    project_code: Mapped[str] = mapped_column(name='КОД ПРОЕКТА')

    def __repr__(self) -> str:
        return (f'Agreements(project_code={self.project_code}')


class AgreementsCollision(AbstractTable):
    """Договора Исключения"""
    project_code_collision: Mapped[str] = mapped_column(name='АКТИВНОСТИ ИСКЛЮЧЕНИЯ')

    def __repr__(self) -> str:
        return (f'AgreementsCollisions(project_code_collision={self.project_code_collision}')
