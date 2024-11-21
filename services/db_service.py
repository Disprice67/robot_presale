from core.interfaces.i_database import IDatabaseRepository, IORMQuary


class DatabaseService:
    def __init__(self, database_repository: IDatabaseRepository):
        self.database_repository = database_repository

    def get_all_tables(self):
        return self.database_repository.get_all_tables()

    def update_table(self, event):
        return self.database_repository.update_table(event)


class ORMService:
    def __init__(self, orm_quary: IORMQuary):
        self.orm_quary = orm_quary

    def directory_books_query(self, item: dict, keys: list):
        return self.orm_quary.directory_books_query(item, keys)

    def category_query(self, item: dict, key: str, comment: str):
        return self.orm_quary.category_query(item, key, comment)
