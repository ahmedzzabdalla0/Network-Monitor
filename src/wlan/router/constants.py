import json
from dataclasses import dataclass

from wlan.managers import EnvManager


@dataclass(frozen=True)
class ZyxelGatewayURLs:
    """Base URLs for the Zyxel VMG3625-T50B router's API."""

    BASE_URL = 'http://192.168.1.1'

    LOGIN = f'{BASE_URL}/UserLogin'
    HOSTS = f'{BASE_URL}/cgi-bin/DAL?oid=lanhosts'
    WLAN = f'{BASE_URL}/cgi-bin/WLANTable_handle'
    LOGOUT = f'{BASE_URL}/cgi-bin/UserLogout'
    NATS = f'{BASE_URL}/cgi-bin/DAL?oid=Traffic_Status'
    SESSIONS = f'{BASE_URL}/cgi-bin/Traffic_Status?mode=NATStatus_handle'
    MENULIST = f'{BASE_URL}/cgi-bin/MenuList'
    CARDINFO = f'{BASE_URL}/cgi-bin/CardInfo'


@dataclass(frozen=True)
class ZyxelLoginConstants:
    """Hardcoded keys and data used for the router's login encryption process."""

    ENV_PREFIX = "ROUTER_"

    KEY = EnvManager.get(ENV_PREFIX + "KEY")
    IV = EnvManager.get(ENV_PREFIX + "IV")
    USERNAME = EnvManager.get(ENV_PREFIX + "USERNAME")
    PASSWORD = EnvManager.get(ENV_PREFIX + "PASSWORD")
    ENCODED_PASSWORD = EnvManager.get(ENV_PREFIX + "ENCODED_PASSWORD")
    ENCRYPTED_CONTENT = EnvManager.get(ENV_PREFIX + "ENCRYPTED_CONTENT")
    ENCRYPTED_KEY = EnvManager.get(ENV_PREFIX + "ENCRYPTED_KEY")
    RSA_PUBLIC_KEY = EnvManager.get(ENV_PREFIX + "RSA_PUBLIC_KEY")
    FINAL_POST_DATA = '"iv": "ZQ9YwwFtzH8+JlstwWUa4zDOtfrZ2MHPODYUc7QhA7I="}'
    POST_DATA = {"content": ENCRYPTED_CONTENT, "key": ENCRYPTED_KEY, "iv": IV}
    FINAL_POST_DATA = json.dumps(POST_DATA, separators=(',', ':'))
    RAW_OBJECT = {"Input_Account": f"{USERNAME}", "Input_Passwd": f"{ENCODED_PASSWORD}=",
                  "currLang": "en", "RememberPassword": 0, "SHA512_password": False}
    RAW_CONTENT = json.dumps(RAW_OBJECT, separators=(',', ':'))
