from typing import Protocol


# DatabaseInterface
class IDatabaseRepository(Protocol):
    def get_all_tables(self):
        ...

    def update_table(self, event):
        ...


class IORMQuary(Protocol):
    def directory_books_query(self, item: dict, keys: list):
        ...

    def category_query(self, item: dict, key: str, comment: str):
        ...
