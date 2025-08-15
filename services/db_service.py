from core.interfaces.i_database import IDatabaseRepository, IORMQuary


class DatabaseService:
    def __init__(self, database_repository: IDatabaseRepository):
        self.database_repository = database_repository

    async def get_all_tables(self):
        return await self.database_repository.get_all_tables()

    async def update_table(self, event):
        return await self.database_repository.update_table(event)


class ORMService:
    def __init__(self, orm_quary: IORMQuary):
        self.orm_quary = orm_quary

    async def directory_books_query(self, item: dict, keys: list, normalized_comment: str):
        return await self.orm_quary.directory_books_query(item, keys, normalized_comment)
