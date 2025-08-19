from typing import Protocol


# DatabaseInterface
class IDatabaseRepository(Protocol):
    async def asyncget_all_tables(self):
        ...

    async def update_table(self, event):
        ...


class IORMQuary(Protocol):
    async def directory_books_query(self, item: dict, keys: list, normalized_comment: str):
        ...
