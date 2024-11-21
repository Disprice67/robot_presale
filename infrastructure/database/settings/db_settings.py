from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class SQLAlchemySettings:
    def __init__(self, url_database: str):
        self.engine = create_engine(url_database, future=True, echo=False)
        self.session_factory = sessionmaker(self.engine)
