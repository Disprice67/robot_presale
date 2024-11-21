from core.interfaces.i_external import IEbay, IEmail, IParsingHuawei
from core.domain_events.eliminations import EliminationFilter
from typing import Optional
from pathlib import Path

class EbayService:
    def __init__(self, ebay: IEbay):
        self.ebay = ebay

    def searchebay(self, item: dict, key: str, vendor: str, ifilter: EliminationFilter) -> None:
        return self.ebay.searchebay(item, key, vendor, ifilter)


class EmailService:
    def __init__(self, email: IEmail,):
        self.email = email

    def get_file_list(self) -> list[Path]:
        return self.email.file_list

    def download_attachments(self,) -> bool:
        return self.email.download_attachments()

    def send_email(self, attachments: Path, sheet_name: str):
        return self.email.send_email(attachments, sheet_name)


class HuaweiService:
    def __init__(self, huawei: IParsingHuawei):
        self.huawei = huawei

    def get_part_and_model(self, key: str) -> Optional[list[str]]:
        return self.huawei.get_part_and_model(key)
