import json
from dataclasses import dataclass

from wlan.managers import ConfigManager, EnvManager


@dataclass(frozen=True)
class ZyxelURLs:
    """Base URLs for the Zyxel VMG3625-T50B router's API."""

    PROTOCOL = ConfigManager.get("router.protocol", "http")
    IP = ConfigManager.get("router.ip", "192.168.1.1")

    BASE_URL = "://".join((PROTOCOL, IP))

    LOGIN = f'{BASE_URL}/UserLogin'
    HOSTS = f'{BASE_URL}/cgi-bin/DAL?oid=lanhosts'
    WLAN = f'{BASE_URL}/cgi-bin/WLANTable_handle'
    LOGOUT = f'{BASE_URL}/cgi-bin/UserLogout'
    NATS = f'{BASE_URL}/cgi-bin/DAL?oid=Traffic_Status'
    SESSIONS = f'{BASE_URL}/cgi-bin/Traffic_Status?mode=NATStatus_handle'
    MENULIST = f'{BASE_URL}/cgi-bin/MenuList'
    CARDINFO = f'{BASE_URL}/cgi-bin/CardInfo'


@dataclass(frozen=True)
class ZyxelLogin:
    """Hardcoded keys and data used for the router's login encryption process."""

    ENV_PREFIX = "ROUTER_"

    ENCRYPTION_KEY = EnvManager.get(
        ENV_PREFIX + "ENCRYPTION_KEY")  # For Login Without Cache
    IV = EnvManager.get(ENV_PREFIX + "IV")  # For Login Without Cache
    USERNAME = EnvManager.get(ENV_PREFIX + "USERNAME")  # For Login
    PASSWORD = EnvManager.get(ENV_PREFIX + "PASSWORD")  # For Login
    ENCRYPTED_CONTENT = EnvManager.get(
        ENV_PREFIX + "ENCRYPTED_CONTENT")  # For Login Without Cache
    ENCRYPTED_KEY = EnvManager.get(
        ENV_PREFIX + "ENCRYPTED_KEY")  # For Login Without Cache
    RSA_PUBLIC_KEY = EnvManager.get(
        ENV_PREFIX + "RSA_PUBLIC_KEY").replace("\\n", "\n")  # For Login (Always Constant)
    POST_DATA = {"content": ENCRYPTED_CONTENT, "key": ENCRYPTED_KEY, "iv": IV}
    FINAL_POST_DATA = json.dumps(POST_DATA, separators=(',', ':'))
    RAW_OBJECT = {"Input_Account": "", "Input_Passwd": "",
                  "currLang": "en", "RememberPassword": 0, "SHA512_password": False}
