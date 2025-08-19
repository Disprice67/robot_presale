from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field, HttpUrl
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
BUFFER_DIR = BASE_DIR / 'infrastructure/folders/buffer'
LOG_FILE = BASE_DIR / 'settings/logs/robot.log'

ENV = os.path.join(os.path.dirname(__file__), ".env")


# Ebay
class Ebay(BaseModel):
    app_id: str
    client_secret: str


# Outlook
class Outlook(BaseModel):
    username_outlook: str
    password_outlook: str
    recipients: str


# Sql_Alchemy
class AlchemyDB(BaseModel):
    url_database: str


# Huawei
class HuaweiHeader(BaseModel):
    user_agent: str = Field(alias="User-Agent")


class HuaweiData(BaseModel):
    header: HuaweiHeader
    url_huawei: HttpUrl


# SYS
class SysData(BaseModel):
    url_sys_agreements: str
    client_id: str
    client_secret: str


# Folders
class Folders(BaseModel):
    ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    FILES_DIR: str = os.path.join(ROOT_DIR, 'files')
    INPUTBUFFER: str = os.path.join(FILES_DIR, 'InputBuffer')
    OUTBUFFER: str = os.path.join(FILES_DIR, 'OutBuffer')


# all_settings
class Settings(BaseSettings):
    outlook: Outlook
    alchemy_db: AlchemyDB
    sysdata: SysData
    huaweidata: HuaweiData
    ebay: Ebay

    class Config:
        env_nested_delimiter = '__'
        env_file = ENV
        env_file_encoding = 'utf-8'
        extra = 'ignore'


try:
    from settings.local_settings import *
except:
    from settings.prod_settings import *
