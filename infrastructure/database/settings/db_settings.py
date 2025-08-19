from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import re
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemySettings:
    def __init__(self, url_database: str):
        self.engine = create_async_engine(url_database, future=True, echo=False)

        @event.listens_for(self.engine.sync_engine, 'connect')
        def register_functions(dbapi_connection, connection_record):
            dbapi_connection.create_function('regexp', 2, self.sqlite_regexp)
            dbapi_connection.create_function('regexp_replace', 3, self.sqlite_regexp_replace)
        
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False
        )

    def sqlite_regexp(self, item, expr):
        """Проверка соответствия регулярному выражению."""
        if item is None:
            return False
        return re.search(expr, item) is not None

    def sqlite_regexp_replace(self, text, pattern, replacement):
        """Замена по регулярному выражению."""
        if text is None:
            return None
        return re.sub(pattern, replacement, text)