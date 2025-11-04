import json
from dataclasses import dataclass

from wlan.managers import ConfigManager, EnvManager


@dataclass(frozen=True)
class TLExtenderURLs:

    PROTOCOL = ConfigManager.get("extender.protocol", "http")
    IP = ConfigManager.get("extender.ip", "192.168.1.207")

    BASE_URL = "://".join((PROTOCOL, IP))

    GET_TOKEN = f'{BASE_URL}/?code=7&asyn=1'
    CONFIRM_ID = f'{BASE_URL}/?code=7&asyn=0'
    HOSTS = f'{BASE_URL}/?code=2&asyn=0'


@dataclass(frozen=True)
class TLExtenderData:

    HOSTS = "13|1,0,0"


@dataclass(frozen=True)
class TLExtenderLogin:
    PASSWORD = EnvManager.get("EXTENDER_PASSWORD")
    HEADERS = dict(Referer=TLExtenderURLs.BASE_URL)
    R_SU_ENCRYPT = EnvManager.get("EXTENDER_R_SU_ENCRYPT")
    T_SU_ENCRYPT = EnvManager.get("EXTENDER_T_SU_ENCRYPT")
