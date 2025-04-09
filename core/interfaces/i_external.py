from core.domain_events.eliminations import EliminationFilter
from typing import Protocol, Optional
from pathlib import Path


# ExternalResourceInterface
class IEbay(Protocol):
    def searchebay(self, item: dict, key: str, vendor: str, ifilter: EliminationFilter) -> None:
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
    def get_part_and_model(self, key: str) -> Optional[list[str]]:
        ...
