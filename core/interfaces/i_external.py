from typing import Protocol, Optional
from pathlib import Path


class IPartNumberFilter(Protocol):
    @staticmethod
    def normalize_part_number(self, part_number: str) -> str:
        """Filter key to ensure it's cleaned and normalized."""
        ...

    def calculate_similarity_score(self, query: str, db_value: str) -> float:
        """Calculate similarity score between query and database value considering length, structure, and suffixes."""
        ...


class IEbay(Protocol):
    async def searchebay(self, item: dict, key: str, vendor: str, ifilter: IPartNumberFilter) -> None:
        ...


class IBouz(Protocol):
    async def search_by_part_number(self, item: str, part_number: str, vendor: str, ifilter: IPartNumberFilter):
        ...


class INag(Protocol):
    def search_by_part_number(self, item: str, part_number: str, vendor: str, ifilter: IPartNumberFilter):
        ...


class IYandexMarket(Protocol):
    async def search_by_part_number(self, item: str, part_number: str, vendor: str, ifilter: IPartNumberFilter):
        ...


class IEmail(Protocol):

    def get_file_list(self) -> list[Path]:
        ...

    def clear_file_list(self) -> None:
        ...

    def download_attachments(self,) -> bool:
        ...

    def send_email(self, attachments: Path, sheet_name: str):
        ...


class IParsingHuawei(Protocol):
    async def get_part_and_model(self, key: str) -> Optional[list[str]]:
        ...
